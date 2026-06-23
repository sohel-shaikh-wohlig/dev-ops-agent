"""
GitHub CLI (gh) Subprocess Wrapper

Thin wrapper around `gh` CLI commands that centralises:
  - subprocess execution (via asyncio.to_thread for non-blocking calls)
  - JSON output parsing (--json flag)
  - error / exit-code → HTTPException mapping
  - logging (redacts --body content)

All GitHub REST API operations in git_service.py and deployment_service.py
route through this helper instead of using httpx directly.
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, status

from app.core.logging_config import logger


# ── result type ─────────────────────────────────────────────────────────

@dataclass
class GHResult:
    """Structured result from a gh CLI invocation."""
    returncode: int
    stdout: str
    stderr: str
    data: Optional[Union[dict, list]] = field(default=None)

    @property
    def ok(self) -> bool:
        return self.returncode == 0


# ── error mapping ───────────────────────────────────────────────────────

def _map_gh_error(result: GHResult, *, repo: Optional[str] = None) -> HTTPException:
    """
    Map a non-zero gh exit code to the most appropriate HTTPException.

    gh CLI exit codes:
      1  — generic failure (usually HTTP 404, 403, 422 from the API)
      2  — command parsing / usage error
      130 — Ctrl-C (SIGINT)
    """
    stderr = (result.stderr or "").strip()

    # ── HTTP-status patterns in gh stderr ──────────────────────────────
    # gh api surfaces the HTTP status in stderr, e.g.:
    #   "HTTP 404: Not Found (https://api.github.com/...)"
    #   "HTTP 422: Validation Failed"
    #   "HTTP 403: Resource not accessible by integration"

    if "HTTP 404" in stderr or "not found" in stderr.lower():
        detail = stderr if repo is None else f"{repo}: {stderr}"
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    if "HTTP 403" in stderr or "forbidden" in stderr.lower():
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API returned 403 Forbidden: {stderr}",
        )

    if "HTTP 422" in stderr or "validation failed" in stderr.lower():
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"GitHub validation error: {stderr}",
        )

    if "HTTP 405" in stderr or "not mergeable" in stderr.lower():
        return HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail=stderr,
        )

    if "HTTP 409" in stderr or "merge conflict" in stderr.lower():
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=stderr,
        )

    # ── connection / network errors ────────────────────────────────────
    if any(s in stderr.lower() for s in ("connect", "timeout", "dns", "network")):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach GitHub API: {stderr}",
        )

    # ── fallback: generic 502 ──────────────────────────────────────────
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"GitHub CLI error (exit {result.returncode}): {stderr}",
    )


# ── core runner ─────────────────────────────────────────────────────────

async def run_gh(
    args: List[str],
    *,
    json_fields: Optional[List[str]] = None,
    timeout: int = 60,
    stdin: Optional[str] = None,
    repo: Optional[str] = None,
) -> GHResult:
    """
    Execute a ``gh`` CLI command asynchronously.

    Parameters
    ----------
    args : list[str]
        Arguments to pass to ``gh`` (excluding the ``gh`` binary itself).
        e.g. ``["api", "repos/tehvault/git-ops/contents/foo"]``
    json_fields : list[str], optional
        If provided, appends ``--json field1,field2,…`` and parses stdout
        as JSON into ``GHResult.data``.
    timeout : int
        Subprocess timeout in seconds (default 60).
    stdin : str, optional
        Text to pipe to the command's stdin.
    repo : str, optional
        Repository identifier (``owner/repo``) for better error messages.

    Returns
    -------
    GHResult
        Structured result including returncode, stdout, stderr, and
        optionally parsed JSON data.

    Raises
    ------
    HTTPException
        If gh exits with a non-zero code, the error is mapped to the
        appropriate HTTP status.
    """
    cmd: List[str] = ["gh"] + list(args)

    if json_fields:
        cmd += ["--json", ",".join(json_fields)]

    # Log the command (redact any --body content for security)
    log_cmd = cmd[:]
    for i, arg in enumerate(log_cmd):
        if i > 0 and log_cmd[i - 1] in ("--body", "--subject") and len(arg) > 20:
            log_cmd[i] = arg[:20] + "…(redacted)"
    logger.debug(f"gh CLI: {' '.join(log_cmd)}")

    def _run() -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=stdin,
        )

    try:
        proc = await asyncio.to_thread(_run)
    except subprocess.TimeoutExpired:
        error_msg = f"gh CLI command timed out after {timeout}s: {' '.join(args[:3])}…"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=error_msg,
        )

    result = GHResult(
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )

    if not result.ok:
        logger.error(
            f"gh CLI failed (exit {result.returncode}): "
            f"args={' '.join(args[:4])}… stderr={result.stderr.strip()[:300]}"
        )
        raise _map_gh_error(result, repo=repo)

    # Parse JSON if requested
    if json_fields and result.stdout.strip():
        try:
            result.data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            logger.warning(f"gh CLI JSON parse failed: {exc}")
            result.data = None

    return result


# ── convenience helpers for common patterns ─────────────────────────────

async def gh_api(
    path: str,
    *,
    method: str = "GET",
    repo: Optional[str] = None,
    timeout: int = 30,
) -> GHResult:
    """
    Run ``gh api <path>`` (or ``gh api -X <method> <path>``).

    Returns parsed JSON in ``result.data``.
    """
    args = ["api", path]
    if method.upper() != "GET":
        args = ["api", "-X", method.upper(), path]

    return await run_gh(args, json_fields=None, timeout=timeout, repo=repo)


async def gh_api_json(
    path: str,
    *,
    method: str = "GET",
    fields: Optional[List[str]] = None,
    repo: Optional[str] = None,
    timeout: int = 30,
) -> Any:
    """
    Run ``gh api`` and return the parsed JSON body directly.

    Uses ``--jq '.'`` to force JSON parsing from the API endpoint.
    (``gh api`` already returns JSON by default — this is a convenience.)
    """
    result = await gh_api(path, method=method, repo=repo, timeout=timeout)
    if not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.warning("gh api: non-JSON response")
        return result.stdout


def check_gh_cli() -> bool:
    """
    Check if gh CLI is installed and callable.

    Called from the FastAPI lifespan startup to warn early if missing.
    """
    try:
        result = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.info(f"gh CLI available: {result.stdout.strip().splitlines()[0]}")
            return True
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_gh_auth() -> bool:
    """
    Check if gh CLI is authenticated.

    Called from the FastAPI lifespan startup to warn early if not authed.
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info("gh CLI authenticated")
            return True
        logger.warning(f"gh CLI auth check failed: {result.stderr.strip()}")
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False