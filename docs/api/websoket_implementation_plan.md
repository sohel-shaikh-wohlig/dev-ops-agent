  ---                                                                                                                                                                              
  1. Current State Summary                                                                                                                                                         
                                                                                                                                                                                   
  What exists today:                                                                                                                                                               
                                                                                                                                                                                   
  - POST /api/github/webhook receives GitHub events, validates HMAC signature, and dispatches to GitHubWebhookService                                                              
  - The service parses Atlantis plan/apply comments and persists PR status to Redis under github:webhook:{pr_number} with a 2-hour TTL                                             
  - GET /api/terraform/pr-status/{pr_number} reads from Redis and returns the status                                                                                               
  - RedisManager (app/core/redis.py) provides a global async connection pool, initialized during app lifespan startup and closed on shutdown
  - CacheService and BaseRedisRepository provide reusable data-access layers on top of redis_manager
  - No WebSocket endpoints exist anywhere in the codebase
  - No Redis Pub/Sub code exists anywhere in the codebase
  - The redis Python package (>=5.0.0) is already installed, which includes redis.asyncio with full Pub/Sub support — no new dependency needed
  - FastAPI 0.115.0 ships with native WebSocket support — no new dependency needed

  What's missing (the gap this plan fills):

  After the webhook service writes to Redis, nothing happens. The React frontend must poll GET /pr-status/{pr_number} to detect changes. There is no push mechanism.

  ---
  2. Target Architecture Design

  GitHub
    │
    ▼
  FastAPI POST /webhook  (Instance A — or any instance)
    │
    ├─► Redis SET (persist PR status)          ← already exists
    │
    └─► Redis PUBLISH on channel               ← NEW
          "pr_updates:{pr_number}"
                │
                ▼
       ┌────────────────────────────────────┐
       │   ALL FastAPI instances subscribe  │   ← NEW
       │   to "pr_updates:*" via a          │
       │   background asyncio task          │
       └────────┬───────────┬───────────────┘
                │           │
          Instance A    Instance B  ...
                │           │
                ▼           ▼
       WebSocketManager  WebSocketManager       ← NEW
       (per-instance)    (per-instance)
                │           │
                ▼           ▼
       Connected WS      Connected WS           ← NEW
       clients for       clients for
       that PR           that PR

  Key design decisions:

  - Redis Pub/Sub is the cross-instance broadcast bus. Every instance subscribes. Only the instance that received the webhook publishes.
  - WebSocket connections are local to each instance. The WebSocketManager only tracks connections on its own process.
  - Channel-per-PR pattern: pr_updates:{pr_number}. Clients subscribe to specific PRs they care about, not a global firehose.
  - Pub/Sub is fire-and-forget. If an instance is down when a message is published, it simply misses it. This is acceptable because the client can always fall back to the REST
  endpoint to get the current state, and will receive the next Pub/Sub update.

  ---
  3. Component Breakdown

  3A. Redis Publisher

  Where it lives: Inside github_webhook_service.py, added to _save_pr_data().

  Responsibility: After every successful SET to Redis, publish the updated PR data to the Pub/Sub channel pr_updates:{pr_number}.

  Behavior:
  - The publish payload is the same JSON blob already being written to Redis (the full PR status dict), plus the pr_number field so subscribers can route it
  - Publishing is best-effort: if it fails, log a warning but do NOT fail the webhook request. The data is already persisted in Redis — Pub/Sub is a notification optimization, not
   the source of truth
  - Uses redis_manager.client.publish() — the same connection pool already in use, no new connections needed

  Channel naming convention: pr_updates:{pr_number} (e.g., pr_updates:42)

  ---
  3B. Redis Subscriber

  New file: app/core/pubsub.py

  Responsibility: A long-running background asyncio.Task that subscribes to pr_updates:* using pattern-subscribe and dispatches incoming messages to the WebSocketManager.

  Behavior:
  - On startup, creates a dedicated Redis connection (separate from the connection pool) for Pub/Sub. This is required because Redis Pub/Sub puts the connection into subscriber
  mode, making it unusable for normal commands
  - Uses redis_manager.client.pubsub() to create a PubSub object, then calls psubscribe("pr_updates:*")
  - Runs an infinite async for message in pubsub.listen() loop inside an asyncio.Task
  - When a message arrives, extracts the pr_number from the channel name and calls ws_manager.broadcast(pr_number, data)
  - If the connection drops, logs the error, waits with exponential backoff (1s, 2s, 4s... capped at 30s), and reconnects

  Lifecycle:
  - Started as a background task during app lifespan startup (after redis_manager.connect())
  - Cancelled during shutdown (before redis_manager.close())
  - The task stores a reference so it can be cleanly cancelled

  ---
  3C. WebSocket Connection Manager

  New file: app/core/websocket_manager.py

  Responsibility: Manages all WebSocket connections for this FastAPI instance. Maps PR numbers to sets of connected WebSocket clients.

  Internal data structure:
  - A dict[int, set[WebSocket]] mapping pr_number to the set of WebSocket connections watching that PR
  - This is instance-local (in-memory) by design — Redis Pub/Sub handles cross-instance fanout

  Methods:
  - connect(pr_number, websocket) — Accept the WebSocket, add it to the set for that PR number
  - disconnect(pr_number, websocket) — Remove from the set; if the set is empty, remove the key entirely (prevents memory leak)
  - broadcast(pr_number, data) — Send JSON data to all connected WebSocket clients watching that PR. For each send, catch exceptions and disconnect dead sockets
  - disconnect_all() — Close all connections gracefully during shutdown

  Memory leak prevention:
  - Dead connections are removed in broadcast() when send_json() raises
  - A client disconnect (detected via WebSocketDisconnect exception in the route handler) triggers disconnect()
  - On app shutdown, disconnect_all() closes and clears everything
  - The dict never holds empty sets — cleaned up on last client disconnect

  Global singleton: ws_manager = WebSocketManager() — instantiated at import time like redis_manager

  ---
  3D. Event Routing Strategy

  How a message gets from Redis to the right WebSocket client:

  1. Webhook handler writes PR status to Redis and publishes to pr_updates:{pr_number}
  2. The subscriber background task on every instance receives the message via psubscribe("pr_updates:*")
  3. The subscriber extracts pr_number from the channel name (e.g., pr_updates:42 → 42)
  4. It calls ws_manager.broadcast(42, data)
  5. The WebSocketManager looks up the set of connections for PR 42 — this set only contains connections local to this instance
  6. It sends the JSON payload to each connected client

  Result: Only clients watching PR #42 on this instance get the message. Clients on other instances get it via their own subscriber → their own WebSocketManager.

  ---
  3E. WebSocket Route

  New file: app/routes/websocket.py

  Endpoint: WS /api/ws/pr-status/{pr_number}

  Behavior:
  1. Accept the WebSocket connection
  2. Register with ws_manager.connect(pr_number, websocket)
  3. Immediately send the current PR status from Redis (so the client doesn't have to wait for the next event)
  4. Enter a receive loop (while True: await websocket.receive_text()) to keep the connection alive and detect client disconnect
  5. On WebSocketDisconnect, call ws_manager.disconnect(pr_number, websocket)

  Why send current state on connect: Eliminates the race condition where a webhook arrives between the client's last REST poll and the WebSocket connection being established.

  ---
  4. Data Flow Explanation

  Complete flow for a single webhook event:

  1. GitHub sends POST /api/github/webhook to Instance A
  2. Controller validates HMAC signature, parses JSON
  3. Service handler (e.g., _handle_issue_comment) processes the event
  4. _save_pr_data() writes the updated PR status dict to Redis:
       SET github:webhook:42 '{"plan_status":"success",...}' EX 7200
  5. _save_pr_data() then publishes:
       PUBLISH pr_updates:42 '{"pr_number":42,"plan_status":"success",...}'
  6. Redis delivers the message to ALL subscribed clients
       (every FastAPI instance has a subscriber task listening on pr_updates:*)
  7. Each instance's subscriber task receives the message
  8. Subscriber calls ws_manager.broadcast(42, data)
  9. WebSocketManager on Instance A sends to its 3 connected WS clients for PR #42
  10. WebSocketManager on Instance B sends to its 1 connected WS client for PR #42
  11. WebSocketManager on Instance C has 0 clients for PR #42 — no-op

  Message format published and sent over WebSocket:

  {
    "pr_number": 42,
    "plan_status": "success",
    "apply_status": "pending",
    "plan_summary": "Add: 2, Change: 0, Destroy: 0",
    "approved": false,
    "state": "open",
    "last_comment": "..."
  }

  This is the same shape as the existing PRStatusResponse model, ensuring the frontend can use the same types for both REST and WebSocket responses.

  ---
  5. FastAPI Lifecycle Integration

  Current lifespan (in main.py):

  startup:
    1. Log startup
    2. Create upload dir
    3. redis_manager.connect()

  shutdown:
    1. Log shutdown
    2. redis_manager.close()
    3. cleanup_old_sessions()

  Proposed lifespan (order matters):

  startup:
    1. Log startup
    2. Create upload dir
    3. redis_manager.connect()           ← existing
    4. Start Pub/Sub subscriber task     ← NEW (must come after Redis is connected)
    5. Log "Pub/Sub subscriber started"  ← NEW

  shutdown:
    1. Log shutdown
    2. Cancel Pub/Sub subscriber task    ← NEW (must come before Redis close)
    3. ws_manager.disconnect_all()       ← NEW (close all WebSocket connections)
    4. redis_manager.close()             ← existing
    5. cleanup_old_sessions()            ← existing

  Why this order:
  - Subscriber must start after Redis is connected (it needs the client)
  - Subscriber must stop before Redis is closed (otherwise it will error trying to unsubscribe)
  - WebSocket connections must be closed before Redis is closed (the initial-state send on connect reads from Redis)

  ---
  6. Horizontal Scaling Behavior

  Scenario: 3 FastAPI instances behind a load balancer

  - Instance A, B, and C all call redis_manager.connect() on startup — 3 independent connection pools to the same Redis
  - All 3 start their Pub/Sub subscriber task, each with a PSUBSCRIBE pr_updates:*
  - A client connects via WebSocket to Instance B (load balancer routes the upgrade request). Instance B's ws_manager tracks this connection
  - A webhook arrives at Instance A. It writes to Redis and publishes to pr_updates:42
  - All 3 instances receive the Pub/Sub message
  - Only Instance B has a WebSocket client for PR #42 — it sends the update
  - Instance A and C receive the message but have no clients for PR #42 — they no-op

  Scaling properties:
  - Adding more instances requires zero configuration — they automatically subscribe
  - WebSocket connections are sticky to the instance they connected to (standard for WebSocket)
  - Redis Pub/Sub fan-out is O(subscribers), which is O(instances) — not O(clients)
  - No shared state between instances except Redis itself

  ---
  7. Failure Scenarios & Recovery Strategy
  ┌──────────────────────────────┬────────────────────────────────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────┐
  │           Scenario           │                       Impact                       │                                         Recovery                                          │
  ├──────────────────────────────┼────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
  │                              │ Webhook writes fail with 503. Pub/Sub subscriber   │ Subscriber reconnects with exponential backoff (1s → 2s → 4s → ... → 30s cap). Once Redis │
  │ Redis goes down              │ loses connection. WebSocket clients stop receiving │  is back, subscriber re-subscribes. Clients that missed updates get current state on next │
  │                              │  updates.                                          │  reconnect or REST poll.                                                                  │
  ├──────────────────────────────┼────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
  │ Subscriber task crashes      │ This instance stops receiving Pub/Sub messages.    │ Wrap the subscriber loop in a top-level try/except that restarts the subscription with    │
  │                              │ Local WebSocket clients stop getting updates.      │ backoff. Log the error. Other instances are unaffected.                                   │
  ├──────────────────────────────┼────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
  │ WebSocket client disconnects │ Normal behavior.                                   │ disconnect() removes the client from ws_manager. If the set for that PR becomes empty,    │
  │                              │                                                    │ the key is deleted. No leaked references.                                                 │
  ├──────────────────────────────┼────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
  │ WebSocket send fails (client │ send_json() raises.                                │ Caught in broadcast(). The dead connection is removed via disconnect(). Remaining clients │
  │  gone but not yet detected)  │                                                    │  still receive the update.                                                                │
  ├──────────────────────────────┼────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
  │ Instance crashes / restarts  │ All WebSocket connections on that instance drop.   │ Clients detect the drop and reconnect (to any instance via load balancer). On connect,    │
  │                              │                                                    │ they receive the current state from Redis.                                                │
  ├──────────────────────────────┼────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
  │ Pub/Sub message lost         │ One update missed by one or more instances.        │ Acceptable. Redis is the source of truth. Client can always REST-poll for current state.  │
  │ (network blip)               │                                                    │ The next Pub/Sub message will deliver the latest state.                                   │
  ├──────────────────────────────┼────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
  │ Redis PUBLISH fails (after   │ Data is persisted but notification not sent.       │ Log a warning. Do NOT fail the webhook. Clients will get the update on next event or REST │
  │ successful SET)              │                                                    │  poll. Publish failure is non-fatal.                                                      │
  └──────────────────────────────┴────────────────────────────────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────┘
  ---
  8. Performance Considerations

  - Pub/Sub is lightweight. PUBLISH is O(N+M) where N = number of pattern subscriptions and M = number of clients subscribed to the channel. With ~3-10 instances, this is trivial.
  - Dedicated Pub/Sub connection. The subscriber uses its own connection, not one from the pool. This prevents blocking pool connections and is the recommended pattern for Redis
  Pub/Sub.
  - No polling. The current REST-based approach requires clients to poll. WebSocket + Pub/Sub eliminates polling entirely, reducing both server load and latency.
  - broadcast() uses asyncio.gather() for parallel sends. Sending to N WebSocket clients is done concurrently, not sequentially.
  - No message persistence in Pub/Sub. Redis Pub/Sub is ephemeral — messages are not stored. This is the right tradeoff because the persisted Redis key IS the source of truth.
  - WebSocketManager dict cleanup. Empty sets are removed immediately, so memory usage is proportional to active connections, not historical ones.

  ---
  9. Security Considerations

  - WebSocket endpoint does NOT require authentication in v1. The PR number is not sensitive (it's a public GitHub PR number), and the data exposed (plan/apply status) is
  operational, not secret. This matches the existing GET /pr-status/{pr_number} which is also unauthenticated.
  - If API key auth is needed later: The WebSocket route can accept the API key as a query parameter (ws://host/api/ws/pr-status/42?api_key=xxx) or via the first message after
  connection. WebSocket does not support custom headers during the upgrade handshake in browsers.
  - Origin validation. FastAPI's CORS middleware does NOT apply to WebSocket upgrades. If origin restriction is needed, validate the Origin header manually in the WebSocket route
  before accepting the connection.
  - Rate limiting. No rate limiting is planned for WebSocket connections in v1. If needed, limit connections per IP at the load balancer or add a per-IP counter in the connect
  handler.
  - Message size. PR status payloads are small (<1KB). No risk of large-message attacks from the server side. The receive loop should ignore or limit incoming client messages
  (they're only used for keepalive detection).

  ---
  10. Implementation Order
  Step: 1
  File: app/core/websocket_manager.py
  Action: Create WebSocketManager class with connect(), disconnect(), broadcast(), disconnect_all()
  Depends On: Nothing
  ────────────────────────────────────────
  Step: 2
  File: app/core/pubsub.py
  Action: Create PubSubSubscriber class with start(), stop(), and the background listener loop with reconnection logic
  Depends On: Step 1 (needs ws_manager to call broadcast)
  ────────────────────────────────────────
  Step: 3
  File: app/services/github_webhook_service.py
  Action: Add PUBLISH call inside _save_pr_data() after the successful SET
  Depends On: Nothing (uses existing redis_manager)
  ────────────────────────────────────────
  Step: 4
  File: app/routes/websocket.py
  Action: Create WebSocket route WS /api/ws/pr-status/{pr_number} with connect/initial-state/receive-loop/disconnect
  Depends On: Steps 1 & 2
  ────────────────────────────────────────
  Step: 5
  File: main.py
  Action: Update lifespan: start subscriber after Redis connect, cancel subscriber + disconnect_all before Redis close. Register the new WebSocket router.
  Depends On: Steps 1-4
  ────────────────────────────────────────
  Step: 6
  File: app/core/config.py
  Action: Add REDIS_PUBSUB_CHANNEL_PREFIX setting (default "pr_updates") for configurability
  Depends On: Nothing (optional, can use hardcoded default)
  ────────────────────────────────────────
  Step: 7
  File: Verify & test
  Action: Manually test: start Redis, start server, connect WebSocket client to ws://localhost:8000/api/ws/pr-status/42, send a test webhook, verify the update arrives over
    WebSocket
  Depends On: Steps 1-5
  ---