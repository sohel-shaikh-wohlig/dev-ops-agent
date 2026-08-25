# Plan: Migrate `/deploy/github` Flow from httpx → `gh` CLI

## Current State

The `/deploy/github` UI (`GitHubDeployPage.tsx`) submits a payload to the backend `POST /api/gitops/micro-service` endpoint, which streams NDJSON logs back. The backend orchestrates a multi-step deployment via `DeploymentService.deploy()`.

### What already uses CLI tools ✅

| Operation | Tool | Location |
|---|---|---|
| Git clone | `git` CLI | `git_service.clone_repository()` |
| Git commit/push | `git` CLI | `git_service.add_all()`, `commit_changes()`, `push_changes()` |
| GitHub secrets | `gh secret set/list` | `git_service.create_repository_secrets()`, `repository_secrets_exist()` |
| PR creation | `gh pr create` | `git_service.create_pull_request()` (used by Terraform flow) |

### What uses httpx (GitHub REST API) and needs migration ❌

| # | Method | File | Lines | GitHub API Call |
|---|---|---|---|---|
| 1 | `get_comment_by_id()` | `api/app/services/git_service.py` | 644–715 | `GET /repos/{repo}/issues/comments/{id}` |
| 2 | `post_pr_comment()` | `api/app/services/git_service.py` | 718–793 | `POST /repos/{repo}/issues/{pr}/comments` |
| 3 | `merge_pull_request()` | `api/app/services/git_service.py` | 796–907 | `PUT /repos/{repo}/pulls/{pr}/merge` |
| 4 | `delete_branch()` | `api/app/services/git_service.py` | 910–985 | `DELETE /repos/{repo}/git/refs/heads/{branch}` |
| 5 | `close_pull_request()` | `api/app/services/git_service.py` | 988–1078 | `PATCH /repos/{repo}/pulls/{pr}` with `state=closed` |
| 6 | `_fetch_workflow_id()` | `api/app/services/deployment_service.py` | 840–875 | `GET /repos/{repo}/actions/runs?head_sha={sha}` |
| 7 | `_poll_workflow_status()` | `api/app/services/deployment_service.py` | 877–914 | `GET /repos/{repo}/actions/runs/{id}` |

> **Note:** Methods 1–5 are *shared* — they serve the Terraform/PR-status routes too, not just `/deploy/github`. Method 6–7 are exclusive to the deploy flow. All 7 should migrate for consistency.

---

## Prerequisites

### 1. Verify `gh` CLI is installed on the backend host

```bash
gh --version          # ≥ 2.40 recommended
gh auth status        # must be authenticated
```

### 2. Ensure `gh` auth token is configured

The backend already reads `GITHUB_TOKEN` from `.env`. `gh` CLI can use this token directly:

```bash
# One-time setup on the server (or set GH_TOKEN env var)
echo "$GITHUB_TOKEN" | gh auth login --with-token
# OR export the env var that gh reads automatically:
export GH_TOKEN="$GITHUB_TOKEN"
```

Add `GH_TOKEN` to the `.env.development` / `.env.uat` files (can reference the same value as `GITHUB_TOKEN`). The `gh` CLI checks `GH_TOKEN` automatically — no `gh auth login` needed if the env var is set.

### 3. Add `gh` to requirements

No pip package needed — `gh` is a system binary. Document the requirement in `api/CLAUDE.md` under Environment Configuration.

---

## Migration Plan

### Phase 1: Create a `gh` CLI helper utility

**New file:** `api/app/utils/gh_cli.py`

A thin wrapper around `subprocess.run(['gh', ...])` that:
- Accepts a list of `gh` CLI args
- Runs the command with `capture_output=True, text=True, timeout=...`
- Parses `--json` output when requested
- Returns a structured result: `(returncode: int, stdout: str, stderr: str, json_data: Optional[dict])`
- Maps non-zero exit codes to appropriate `HTTPException` status codes (404, 422, 502, etc.)
- Uses `asyncio.to_thread()` for non-blocking execution from async FastAPI handlers
- Logs the command being run (redacting any `--body` content that may contain secrets)

```python
# Pseudocode for the helper
class GHCLIResult:
    returncode: int
    stdout: str
    stderr: str
    data: Optional[dict | list]  # parsed JSON if --json flag used

async def run_gh(args: list[str], *, json_fields: list[str] = None, timeout: int = 30) -> GHCLIResult:
    cmd = ['gh'] + args
    if json_fields:
        cmd += ['--json', ','.join(json_fields)]
    result = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, timeout=timeout)
    # parse, map errors, return
```

### Phase 2: Migrate `git_service.py` methods (5 methods)

#### 2.1 `get_comment_by_id()` → `gh api`

**Current:** `httpx.AsyncClient().get("https://api.github.com/repos/{repo}/issues/comments/{id}")`

**New:**
```bash
gh api repos/{repo}/issues/comments/{comment_id} --jq '.'
```
- Exit code 0 → parse stdout as JSON, return dict
- Exit code 1 + stderr contains "not found" → `HTTPException(404)`
- Other failures → `HTTPException(502)`

**Signature unchanged:** `(comment_id: int, repo_name: Optional[str] = None) -> dict`

#### 2.2 `post_pr_comment()` → `gh pr comment`

**Current:** `httpx.AsyncClient().post("https://api.github.com/repos/{repo}/issues/{pr}/comments")`

**New:**
```bash
echo "{comment}" | gh pr comment {pr_number} --body-file - -R {repo_name}
```
- Or use `--body "{comment}"` for short comments (beware shell-escaping; prefer stdin via `--body-file -`)
- Exit code 0 → parse the JSON output (add `--json id,body,createdAt` if structured return needed)
- Exit code 1 + "not found" → `HTTPException(404)`
- Other → `HTTPException(502)`

**Signature unchanged:** `(pr_number: int, comment: str, repo_name: Optional[str] = None) -> dict`

#### 2.3 `merge_pull_request()` → `gh pr merge`

**Current:** `httpx.AsyncClient().put("https://api.github.com/repos/{repo}/pulls/{pr}/merge")`

**New:**
```bash
gh pr merge {pull_number} --{merge_method} -R {repo_name} \
  --subject "{commit_title}" --body "{commit_message}"
```
- `merge_method` maps directly: `squash` → `--squash`, `merge` → `--merge`, `rebase` → `--rebase`
- Exit code 0 → return `{"sha": ..., "merged": true, "message": "Pull request merged"}`
  - Add `--json sha,merged,message` for structured output
- Exit code 1 + "not mergeable" → `HTTPException(405)`
- Exit code 1 + "merge conflict" → `HTTPException(409)`
- Exit code 1 + "not found" → `HTTPException(404)`
- Other → `HTTPException(502)`

**Signature unchanged:** `(pull_number, commit_title, commit_message, merge_method, repo_name) -> dict`

#### 2.4 `delete_branch()` → `gh api -X DELETE`

**Current:** `httpx.AsyncClient().delete("https://api.github.com/repos/{repo}/git/refs/heads/{branch}")`

**New:**
```bash
gh api -X DELETE repos/{repo}/git/refs/heads/{branch_name}
```
- `gh` doesn't have a direct `gh repo delete-branch` command for arbitrary branch refs, but `gh api -X DELETE` works perfectly
- Exit code 0 → `{"branch": branch_name, "deleted": True}`
- Exit code 1 + "not found" → `HTTPException(404)`
- Other → `HTTPException(502)`

**Signature unchanged:** `(branch_name: str, repo_name: Optional[str] = None) -> dict`

#### 2.5 `close_pull_request()` → `gh pr close`

**Current:** `httpx.AsyncClient().patch("https://api.github.com/repos/{repo}/pulls/{pr}")` with `{"state": "closed"}`

**New:**
```bash
gh pr close {pull_number} -R {repo_name}
```
- Exit code 0 → `{"pull_number": pull_number, "state": "closed", "closed": True}`
- Exit code 1 + "not found" → `HTTPException(404)`
- Exit code 1 + "already closed" → `HTTPException(422)`
- Other → `HTTPException(502)`

**Signature unchanged:** `(pull_number: int, repo_name: Optional[str] = None) -> dict`

### Phase 3: Migrate `deployment_service.py` methods (2 methods)

#### 3.1 `_fetch_workflow_id()` → `gh run list`

**Current:**
```python
httpx.get(f"https://api.github.com/repos/{owner_repo}/actions/runs?head_sha={commit_hash}")
```
with retry logic (up to 10 retries, 10s delay).

**New:**
```bash
gh run list --commit {commit_hash} -R {owner_repo} --json databaseId,status --limit 1
```
- Parse `databaseId` from JSON output → return as `workflow_id`
- If empty array → no runs found yet → retry (keep existing retry loop)
- Keep the existing `WORKFLOW_FETCH_MAX_RETRIES` / `WORKFLOW_FETCH_RETRY_DELAY` constants and retry loop structure — just swap the inner `httpx.get()` call for `await run_gh([...])`
- The `httpx.AsyncClient` parameter in the method signature can be removed (it was only used for the HTTP call)

**Signature change:** Remove `client: httpx.AsyncClient` and `headers: Dict[str, str]` parameters. Keep `github_action_domain: str` (or replace with `owner_repo: str`) and `commit_hash: str`.

#### 3.2 `_poll_workflow_status()` → `gh run view`

**Current:**
```python
httpx.get(f"https://api.github.com/repos/{owner_repo}/actions/runs/{workflow_id}")
```
in a polling loop (up to 60 attempts, 10s interval).

**New:**
```bash
gh run view {workflow_id} -R {owner_repo} --json status,conclusion
```
- Parse `status` and `conclusion` from JSON output
- Keep the existing `WORKFLOW_POLL_MAX_ATTEMPTS` / `WORKFLOW_POLL_INTERVAL` polling loop — just swap the inner `httpx.get()` call
- Exit code 1 + "not found" → raise `Exception` (workflow doesn't exist)

**Signature change:** Same as 3.1 — remove `client` and `headers` params. Replace with `owner_repo: str` and `workflow_id: int`.

#### 3.3 Update `_monitor_and_deploy()` caller

The parent method `_monitor_and_deploy()` currently:
1. Constructs `github_action_domain` URL and `github_headers` dict
2. Creates `httpx.AsyncClient()` context manager
3. Calls `_fetch_workflow_id(client, domain, headers, hash)`
4. Calls `_poll_workflow_status(client, domain, headers, id)`

**After migration:**
1. Extract `owner_repo` from the microservice URL (same parsing logic already exists)
2. Call `_fetch_workflow_id(owner_repo, commit_hash)` — no client/headers needed
3. Call `_poll_workflow_status(owner_repo, workflow_id)` — no client/headers needed
4. Remove `import httpx` from `deployment_service.py` (if no other httpx usage remains — check: the `httpx` import is also used by `_monitor_and_deploy` for the `AsyncClient`, which will no longer be needed)

### Phase 4: Cleanup & Documentation

#### 4.1 Remove `httpx` dependency from `git_service.py`

After all 5 methods migrate, the `import httpx` at line 12 of `git_service.py` can be removed. Verify no other method in the file uses httpx.

#### 4.2 Remove `httpx` dependency from `deployment_service.py`

After methods 6–7 migrate, the `import httpx` at line 14 can be removed. Verify: `httpx` is also imported but only used in `_monitor_and_deploy` (the `AsyncClient` context manager).

#### 4.3 Update `api/CLAUDE.md`

Add to the Environment Configuration section:
```
- `GH_TOKEN`: GitHub CLI token (automatically read by `gh` CLI; can be same as `GITHUB_TOKEN`)
- `gh` CLI must be installed and authenticated on the backend host
```

Add to Key Patterns section:
```
**GitHub CLI (gh)**: All GitHub API operations (comments, merges, branch deletion, PR status, workflow monitoring) use the `gh` CLI via subprocess, not direct REST API calls. This centralizes authentication and rate-limit handling through `gh`.
```

#### 4.4 Update top-level `CLAUDE.md`

Add `gh` to the MCP Tools or Architecture section as a runtime dependency.

#### 4.5 Update `requirements.txt`

No change — `gh` is a system binary, not a pip package. But add a comment or a check script:

**New file:** `api/app/utils/gh_check.py` (optional, for startup health check)
```python
import subprocess
def check_gh_cli() -> bool:
    result = subprocess.run(['gh', '--version'], capture_output=True, text=True, timeout=5)
    return result.returncode == 0
```
Could be called in `main.py` lifespan startup to warn if `gh` is missing.

---

## File Change Summary

| File | Change Type | Description |
|---|---|---|
| `api/app/utils/gh_cli.py` | **NEW** | `gh` CLI subprocess wrapper helper |
| `api/app/services/git_service.py` | **MODIFY** | Replace httpx calls in 5 methods with `gh` CLI calls |
| `api/app/services/deployment_service.py` | **MODIFY** | Replace httpx calls in 2 methods + update `_monitor_and_deploy` caller |
| `api/CLAUDE.md` | **MODIFY** | Document `gh` CLI dependency |
| `CLAUDE.md` (root) | **MODIFY** | Add `gh` to runtime deps |

**Files NOT modified:**
- `frontend/` — no changes needed. The frontend talks to the FastAPI backend via REST/NDJSON; the backend's internal switch from httpx to `gh` CLI is transparent.
- `devops_mcp/` — no changes needed. The MCP server calls the FastAPI backend, not GitHub directly.
- `api/app/routes/` — no changes needed. Route signatures and response shapes are unchanged.
- `api/app/controllers/` — no changes needed. Controllers delegate to services; service signatures stay the same.

---

## Method-by-Method Migration Detail

### `get_comment_by_id` (git_service.py:644)

```
BEFORE:
  httpx.get("https://api.github.com/repos/{repo}/issues/comments/{id}")
  → parse response.json()

AFTER:
  gh api repos/{repo}/issues/comments/{id}
  → parse stdout as JSON
```

Error mapping:
- HTTP 404 → `gh` exit code 1, stderr "HTTP 404: Not Found" → `HTTPException(404)`
- HTTP 403 → `gh` exit code 1, stderr "HTTP 403" → `HTTPException(502, "GitHub API returned 403")`
- Connection error → `gh` exit code 1, stderr contains "connect" → `HTTPException(502)`

### `post_pr_comment` (git_service.py:718)

```
BEFORE:
  httpx.post("https://api.github.com/repos/{repo}/issues/{pr}/comments", json={"body": comment})

AFTER:
  echo "{comment}" | gh pr comment {pr} -R {repo} --body-file -
  # OR for structured return:
  echo "{comment}" | gh pr comment {pr} -R {repo} --body-file - --json id,body,createdAt,author
```

Prefer `--body-file -` (stdin) to avoid shell-escaping issues with comment bodies containing quotes, backticks, or special chars.

### `merge_pull_request` (git_service.py:796)

```
BEFORE:
  httpx.put("https://api.github.com/repos/{repo}/pulls/{pr}/merge", json={commit_title, commit_message, merge_method})

AFTER:
  gh pr merge {pr} -R {repo} --{merge_method} --subject "{commit_title}" --body "{commit_message}" --json sha,merged,message
```

Method mapping:
- `squash` → `--squash`
- `merge` → `--merge`
- `rebase` → `--rebase`

### `delete_branch` (git_service.py:910)

```
BEFORE:
  httpx.delete("https://api.github.com/repos/{repo}/git/refs/heads/{branch}")

AFTER:
  gh api -X DELETE repos/{repo}/git/refs/heads/{branch}
```

No dedicated `gh` command for arbitrary ref deletion — `gh api -X DELETE` is the idiomatic approach.

### `close_pull_request` (git_service.py:988)

```
BEFORE:
  httpx.patch("https://api.github.com/repos/{repo}/pulls/{pr}", json={"state": "closed"})

AFTER:
  gh pr close {pr} -R {repo}
```

### `_fetch_workflow_id` (deployment_service.py:840)

```
BEFORE:
  httpx.get("https://api.github.com/repos/{owner_repo}/actions/runs?head_sha={sha}")

AFTER:
  gh run list --commit {sha} -R {owner_repo} --json databaseId --limit 1
```

Parse `databaseId` from the JSON array. Keep the retry loop as-is.

### `_poll_workflow_status` (deployment_service.py:877)

```
BEFORE:
  httpx.get("https://api.github.com/repos/{owner_repo}/actions/runs/{id}")

AFTER:
  gh run view {id} -R {owner_repo} --json status,conclusion
```

Parse `status` and `conclusion` from JSON output. Keep the polling loop as-is.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `gh` CLI not installed on deployment host | Add startup health check in `main.py` lifespan; document in README |
| `gh` auth not configured | Set `GH_TOKEN` env var (same as `GITHUB_TOKEN`); document in `.env.example` |
| Shell injection via comment bodies / commit messages | Use `subprocess.run()` with list args (never `shell=True`); pass comment body via stdin (`--body-file -`) |
| `gh` CLI rate limits differ from direct API | `gh` uses the same GitHub API under the hood — same rate limits apply. No change needed. |
| `gh` CLI output format changes across versions | Pin `gh` version in deployment docs (≥ 2.40). Use `--json` flag for stable structured output. |
| Async blocking from subprocess calls | All calls wrapped in `asyncio.to_thread()` (existing pattern already used for `git` CLI calls) |
| Branch names with slashes (e.g. `tf/client/dev/gcs/...`) | `gh api` handles URL-encoding; test with the existing test case branch names |
| Large comment bodies exceeding shell arg limits | Use `--body-file -` (stdin) instead of `--body "{text}"` |

---

## Testing Checklist

- [ ] `gh auth status` passes on the backend host
- [ ] `POST /api/gitops/micro-service` deployment completes end-to-end with `gh` CLI
- [ ] `GET /api/github/comments/{id}` returns a comment
- [ ] `POST /api/github/comments` posts a comment on a test PR
- [ ] `POST /api/github/pulls/{n}/merge` merges a test PR
- [ ] `DELETE /api/github/branches/{name}` deletes a test branch
- [ ] `PATCH /api/github/pulls/{n}/close` closes a test PR
- [ ] `GET /api/terraform/pr-status/{n}` still works (uses `github_webhook_service`, not affected)
- [ ] Workflow monitoring: `_fetch_workflow_id` + `_poll_workflow_status` work with `gh run list/view`
- [ ] Error cases: 404 (not found), 422 (validation), 502 (GitHub API error) all return correct HTTP status codes
- [ ] NDJSON streaming still works (log output format unchanged)

---

## Implementation Order

1. Create `api/app/utils/gh_cli.py` helper
2. Migrate `git_service.py` methods one at a time (test each):
   - `get_comment_by_id`
   - `post_pr_comment`
   - `merge_pull_request`
   - `delete_branch`
   - `close_pull_request`
3. Migrate `deployment_service.py` methods:
   - `_fetch_workflow_id`
   - `_poll_workflow_status`
   - Update `_monitor_and_deploy` to remove httpx client/headers
4. Remove `import httpx` from both files
5. Update documentation (`CLAUDE.md`, `README.md`)
6. Run full deployment test via `/deploy/github` UI