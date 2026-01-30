### Data Flow Diagram
┌─────────────────────────────────────────────────────────────────┐
│                         AI Client                               │
│                    (Claude Desktop)                             │
└──────────────┬──────────────────────────────────────────────────┘
               │
               │ "Deploy user-service to staging"
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      MCP Servers                                 │
│                                                                  │
│  ┌─────────────────────┐         ┌───────────────────────┐       │
│  │ devops_automation   │         │  kubernetes_multi     │       │
│  │                     │         │                       │       │
│  │ Uses:               │         │ Uses:                 │       │
│  │ • api_client        │         │ • kubectl commands    │       │
│  │ • settings          │         │ • contexts config     │       │
│  │ • deployment_tools  │         │ • k8s_tools           │       │
│  └──────────┬──────────┘         └──────────┬────────────┘       │
│             │                               │                    │
└─────────────┼───────────────────────────────┼────────────────────┘
              │                               │
              │ HTTP/JSON                     │ kubectl commands
              │                               │
              ▼                               ▼
┌──────────────────────────┐    ┌────────────────────────────┐
│   Your FastAPI Backend   │    │    GKE Clusters            │
│                          │    │  • dev-cluster             │
│  /gitops/micro-service   │    │  • staging-cluster         │
│  /gitops/deployments     │    │  • prod-cluster            │
│                          │    │                            │
│  Uses:                   │    └────────────────────────────┘
│  • gitops_service.py     │
│  • argocd_service.py     │
│  • github_service.py     │
│  • cloudflare_service.py │
└──────────────────────────┘


### Import Relationships
mcp/servers/devops_automation.py
    ├── imports: mcp.shared.api_client
    ├── imports: mcp.config.settings
    ├── imports: mcp.tools.deployment_tools
    └── calls: FastAPI endpoints via api_client

mcp/servers/kubernetes_multi.py
    ├── imports: mcp.config.settings
    ├── imports: mcp.config.contexts
    └── calls: kubectl commands

mcp/shared/api_client.py
    ├── imports: httpx
    ├── imports: logging
    └── called by: all MCP servers

mcp/config/settings.py
    ├── imports: pydantic_settings
    ├── reads: .env file
    └── used by: all MCP components

mcp/tools/deployment_tools.py
    ├── imports: mcp.types
    └── provides: Tool schemas


### Configuration Flow
.env (environment variables)
    ↓
mcp/config/settings.py (loads and validates)
    ↓
mcp/servers/* (use settings)
    ↓
Claude Desktop config.json (references servers)
    ↓
AI Client (runs servers with settings)

### MCP Server Running Modes
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server Running Modes                     │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│  1. STANDALONE       │  │  2. WITH INSPECTOR   │  │  3. CLAUDE DESKTOP   │
│  (Quick Test)        │  │  (Development)       │  │  (Production)        │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
         │                          │                          │
         ▼                          ▼                          ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ $ python             │  │ $ mcp-inspector      │  │ claude_desktop_      │
│   mcp/servers/       │  │   python mcp/        │  │   config.json        │
│   devops.py          │  │   servers/devops.py  │  │                      │
│                      │  │                      │  │ {                    │
│ [Waiting for stdin]  │  │ ✓ Web UI opens       │  │   "mcpServers": {    │
│ [Press Ctrl+C]       │  │   localhost:5173     │  │     "devops": {...}  │
│                      │  │                      │  │   }                  │
│ Use: Quick testing   │  │ Use: Development     │  │ }                    │
│      Debugging       │  │      Interactive     │  │                      │
│                      │  │      testing         │  │ Use: Production      │
│                      │  │                      │  │      AI interaction  │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘


### Mode 1: Standalone (Quick Test)
┌─────────────────────────────────────────────────────────────┐
│ Terminal                                                    │
├─────────────────────────────────────────────────────────────┤
│ $ python mcp/servers/devops_automation.py                   │
│ ▊                                                           │
│ [Server is running, waiting for MCP protocol input]         │
│ [No visible output is normal]                               │
│ [Press Ctrl+C to stop]                                      │
└─────────────────────────────────────────────────────────────┘

What's happening:
- Server reads from stdin (standard input)
- Writes to stdout (standard output)
- Uses MCP protocol (JSON-RPC over stdio)
- Perfect for checking if server starts without errors

When to use:
✓ Quick syntax check
✓ Verify server starts
✓ Check import errors
✗ NOT for testing tools (no way to send MCP messages manually)

### Mode 2: With MCP Inspector (Development)
┌─────────────────────────────────────────────────────────────┐
│ Terminal                                                     │
├─────────────────────────────────────────────────────────────┤
│ $ mcp-inspector python mcp/servers/devops_automation.py     │
│                                                             │
│ ✓ MCP Inspector running at http://localhost:5173           │
│ ✓ Server connected: devops-automation                      │
│ ✓ Tools available: 5                                       │
│                                                             │
│ Opening browser...                                         │
└─────────────────────────────────────────────────────────────┘

                    ↓ Opens in browser ↓

┌─────────────────────────────────────────────────────────────┐
│ http://localhost:5173                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🔧 MCP Inspector                                           │
│                                                             │
│  Server: devops-automation  [Connected ✓]                   │
│                                                             │
│  📋 Available Tools:                                         |
│  ┌──────────────────────────────────────────────┐           │
│  │ ▶ deploy_microservice                        │           │
│  │   Deploy a microservice to GKE cluster       │           │
│  │   [Test Tool]                                │           │
│  └──────────────────────────────────────────────┘           │
│  ┌──────────────────────────────────────────────┐           │
│  │ ▶ check_deployment_status                    │           │
│  │   Check deployment status                    │           │
│  │   [Test Tool]                                │           │
│  └──────────────────────────────────────────────┘           │
│                                                             │
│  [Click on any tool to test it interactively]               │
└─────────────────────────────────────────────────────────────┘

When to use:
✓ Development and testing
✓ Debugging tool calls
✓ Seeing tool responses
✓ Validating tool schemas
✓ Testing before deploying to Claude


### Mode 3: Claude Desktop (Production)
Step 1: Configure
───────────────────────────────────────────────────────────
~/Library/Application Support/Claude/claude_desktop_config.json

{
  "mcpServers": {
    "devops-automation": {
      "command": "python",
      "args": ["/Users/you/project/mcp/servers/devops_automation.py"],
      "env": {
        "MCP_FASTAPI_URL": "http://localhost:8000"
      }
    }
  }
}

Step 2: Restart Claude Desktop
───────────────────────────────────────────────────────────
macOS:  Cmd+Q, then reopen
Windows: Right-click tray icon → Quit, then reopen
Linux:  killall claude, then relaunch

Step 3: Automatic startup
───────────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────┐
│ Claude Desktop                                        │
├──────────────────────────────────────────────────────┤
│                                                       │
│  [Starting MCP servers...]                           │
│  ✓ devops-automation: Connected                      │
│  ✓ kubernetes: Connected                             │
│                                                       │
│  [Ready to chat]                                     │
└──────────────────────────────────────────────────────┘

Step 4: Use in conversation
───────────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────┐
│ Claude                                                │
├──────────────────────────────────────────────────────┤
│                                                       │
│  You: Deploy user-service to staging                 │
│                                                       │
│  Claude: I'll help you deploy user-service to        │
│  staging. Let me check a few things first...         │
│                                                       │
│  [Calls k8s_get_pods(environment='staging')]         │
│  [Calls deploy_microservice(...)]                    │
│                                                       │
│  ✓ Deployment successful!                            │
│  Service: user-service                               │
│  Environment: staging                                │
│  URL: https://user-service-staging.example.com       │
│                                                       │
└──────────────────────────────────────────────────────┘

When to use:
✓ Production use
✓ AI-powered deployments
✓ Natural language interface
✓ Daily operations


### Process Flow Comparison
#### Standalone Mode
You → python command → MCP Server → (waiting for stdin)
                                   ↓
                          [No visible output]
                          [Use Ctrl+C to stop]

#### Inspector Mode
You → mcp-inspector command → Inspector (web server)
                               ↓
                        Spawns → MCP Server
                               ↓
                        Browser UI ← Inspector ← MCP Server
                               ↓
                        You interact with UI
                               ↓
                        Inspector sends MCP messages
                               ↓
                        MCP Server responds
                               ↓
                        Results shown in Browser

#### Claude Desktop Mode
Claude Desktop starts → Reads config.json
                               ↓
                        Spawns MCP Servers automatically
                               ↓
        User chats → Claude AI → Decides to use tools
                               ↓
                        Sends MCP protocol messages
                               ↓
                        MCP Server executes
                               ↓
                        Calls your FastAPI
                               ↓
                        Returns result to Claude
                               ↓
                        Claude shows result to user