"""
Git Utilities Service
Handles Git operations: clone, pull, commit, push
Based on original script's git functionality
"""
import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple, List

import httpx
from fastapi import HTTPException, status

from app.core.logging_config import logger
from app.core.config import get_settings


class GitUtilitiesService:
    """
    Service for Git operations
    Mirrors the original script's git functionality
    """
    
    @staticmethod
    def _build_clone_url(git_url: str) -> str:
        """
        Build the clone URL based on the URL format.
        - SSH URLs (git@github.com:...) are used as-is
        - HTTPS URLs get the GITHUB_TOKEN injected for authentication

        Args:
            git_url: Original Git repository URL

        Returns:
            Clone-ready URL
        """
        if git_url.startswith("git@"):
            logger.info("Detected SSH URL, cloning via SSH")
            return git_url

        if git_url.startswith("https://"):
            settings = get_settings()
            token = settings.GITHUB_TOKEN
            if token and token != "GITHUB_TOKEN":
                authenticated_url = git_url.replace("https://", f"https://{token}@")
                logger.info("Detected HTTPS URL, cloning with token authentication")
                return authenticated_url
            logger.info("Detected HTTPS URL, cloning without token (no valid GITHUB_TOKEN configured)")

        return git_url

    @staticmethod
    def _https_to_ssh(https_url: str) -> Optional[str]:
        """
        Convert an HTTPS GitHub URL to its SSH equivalent.

        e.g. https://github.com/org/repo  ->  git@github.com:org/repo.git

        Returns None if the URL cannot be converted.
        """
        try:
            url = https_url.split("@")[-1] if "@" in https_url else https_url
            url = url.removeprefix("https://").removeprefix("http://")
            parts = url.rstrip("/").removesuffix(".git").split("/")
            if len(parts) < 3:
                return None
            host = parts[0]
            owner_repo = "/".join(parts[1:3])
            return f"git@{host}:{owner_repo}.git"
        except Exception:
            return None

    @staticmethod
    def clone_repository(
        git_url: str,
        target_dir: Path,
        branch: str = "dev",
        depth: int = 1
    ) -> Tuple[bool, Optional[str]]:
        """
        Clone a Git repository (supports both HTTPS and SSH URLs)

        Args:
            git_url: Git repository URL (HTTPS or SSH)
            target_dir: Target directory for clone
            branch: Branch to clone (default: main)
            depth: Clone depth (default: 1 for shallow clone)

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Remove target directory if it exists
            if target_dir.exists():
                logger.info(f"Removing existing directory: {target_dir}")
                shutil.rmtree(target_dir)

            # Create parent directory
            target_dir.parent.mkdir(parents=True, exist_ok=True)

            clone_url = GitUtilitiesService._build_clone_url(git_url)
            logger.info(f"Cloning repository: {git_url} to {target_dir}")

            def _try_clone(url: str) -> "subprocess.CompletedProcess[str]":
                """Attempt clone with branch, then without branch."""
                res = subprocess.run(
                    ['git', 'clone', '--branch', branch, '--depth', str(depth), url, str(target_dir)],
                    capture_output=True, text=True, timeout=300,
                )
                if res.returncode != 0:
                    logger.warning(f"Branch '{branch}' not found for {url}, trying default branch")
                    if target_dir.exists():
                        shutil.rmtree(target_dir)
                    res = subprocess.run(
                        ['git', 'clone', '--depth', str(depth), url, str(target_dir)],
                        capture_output=True, text=True, timeout=300,
                    )
                return res

            result = _try_clone(clone_url)

            if result.returncode != 0 and git_url.startswith("https://"):
                # HTTPS failed — retry with SSH equivalent
                ssh_url = GitUtilitiesService._https_to_ssh(git_url)
                if ssh_url:
                    logger.warning(
                        f"HTTPS clone failed, retrying with SSH: {ssh_url}"
                    )
                    result = _try_clone(ssh_url)

            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error during clone"
                logger.error(f"Git clone failed: {error_msg}")
                return False, error_msg

            logger.info(f"Repository cloned successfully to {target_dir}")
            return True, None

        except subprocess.TimeoutExpired:
            error_msg = "Git clone operation timed out (5 minutes)"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Failed to clone repository: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def find_git_root(start_path: Path) -> Optional[Path]:
        """
        Find the root of the git repository starting from path
        (Original: find_git_root)
        
        Args:
            start_path: Starting path to search from
            
        Returns:
            Path to git root or None if not found
        """
        current_path = start_path.resolve()
        
        while current_path != current_path.parent:
            if (current_path / ".git").is_dir():
                logger.info(f"Found git root: {current_path}")
                return current_path
            current_path = current_path.parent
        
        logger.warning(f"Could not find .git directory in parent hierarchy of {start_path}")
        return None
    
    @staticmethod
    def run_git_command(args: List[str], cwd: Path) -> Tuple[bool, Optional[str]]:
        """
        Run a git command
        (Original: run_git_command)
        
        Args:
            args: Git command arguments (without 'git' prefix)
            cwd: Working directory
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            logger.debug(f"Running git command: git {' '.join(args)} in {cwd}")
            
            result = subprocess.run(
                ['git'] + args,
                cwd=cwd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120  # 2 minutes timeout
            )
            
            logger.debug(f"Git command succeeded: {result.stdout.strip()}")
            return True, None
            
        except subprocess.CalledProcessError as e:
            # Capture both stdout and stderr for better error reporting
            error_details = e.stderr.strip() if e.stderr else ""
            stdout_details = e.stdout.strip() if e.stdout else ""
            combined_output = error_details or stdout_details or "No error details available"
            error_msg = f"Git command failed: git {' '.join(args)}\nError: {combined_output}"
            logger.error(error_msg)
            return False, error_msg
        except subprocess.TimeoutExpired:
            error_msg = f"Git command timed out: git {' '.join(args)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error running git command: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def pull_latest(repo_dir: Path) -> Tuple[bool, Optional[str]]:
        """
        Pull latest changes from remote
        
        Args:
            repo_dir: Repository directory
            
        Returns:
            Tuple of (success, error_message)
        """
        logger.info(f"Pulling latest changes in {repo_dir}")
        success, error = GitUtilitiesService.run_git_command(['pull'], repo_dir)
        
        if success:
            logger.info("Git pull successful")
        else:
            logger.warning(f"Git pull failed: {error}")
        
        return success, error
    
    @staticmethod
    def add_all(repo_dir: Path) -> Tuple[bool, Optional[str]]:
        """
        Add all changes to staging
        
        Args:
            repo_dir: Repository directory
            
        Returns:
            Tuple of (success, error_message)
        """
        logger.info(f"Adding all changes in {repo_dir}")
        return GitUtilitiesService.run_git_command(['add', '.'], repo_dir)
    
    @staticmethod
    def commit_changes(
        repo_dir: Path,
        commit_message: str,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Commit changes to repository

        Args:
            repo_dir: Repository directory
            commit_message: Commit message
            author_name: Git author name (defaults to env GIT_USER_NAME)
            author_email: Git author email (defaults to env GIT_USER_EMAIL)

        Returns:
            Tuple of (success, error_message, commit_hash)
        """
        settings = get_settings()

        # Use provided values or fall back to settings
        git_user_name = author_name or settings.GIT_USER_NAME
        git_user_email = author_email or settings.GIT_USER_EMAIL

        logger.info(f"Committing changes with message: {commit_message}")

        # Configure git user for this repository
        GitUtilitiesService.run_git_command(
            ['config', 'user.name', git_user_name],
            repo_dir
        )
        GitUtilitiesService.run_git_command(
            ['config', 'user.email', git_user_email],
            repo_dir
        )

        # Check if there are staged changes before committing
        try:
            status_result = subprocess.run(
                ['git', 'diff', '--cached', '--quiet'],
                cwd=repo_dir,
                capture_output=True,
                text=True
            )
            if status_result.returncode == 0:
                # No staged changes
                logger.warning("No changes to commit - files may already be up to date")
                return True, None, None  # Return success with no commit hash
        except Exception as e:
            logger.warning(f"Could not check staged changes: {e}")

        success, error = GitUtilitiesService.run_git_command(
            ['commit', '-m', commit_message],
            repo_dir
        )

        if not success:
            # Check if it's a "nothing to commit" error
            if error and ("nothing to commit" in error.lower() or "no changes" in error.lower()):
                logger.info("No changes to commit - working tree clean")
                return True, None, None
            return False, error, None
        
        # Get commit hash
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=True
            )
            commit_hash = result.stdout.strip()
            logger.info(f"Commit successful. Hash: {commit_hash}")
            return True, None, commit_hash
            
        except Exception as e:
            logger.warning(f"Failed to get commit hash: {e}")
            return True, None, None
    
    @staticmethod
    def push_changes(repo_dir: Path) -> Tuple[bool, Optional[str]]:
        """
        Push changes to remote repository
        
        Args:
            repo_dir: Repository directory
            
        Returns:
            Tuple of (success, error_message)
        """
        logger.info(f"Pushing changes from {repo_dir}")
        success, error = GitUtilitiesService.run_git_command(['push'], repo_dir)
        
        if success:
            logger.info("Git push successful")
        else:
            logger.error(f"Git push failed: {error}")
        
        return success, error
    
    @staticmethod
    def get_current_branch(repo_dir: Path) -> Optional[str]:
        """
        Get current Git branch name
        
        Args:
            repo_dir: Repository directory
            
        Returns:
            Branch name or None
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()
            logger.info(f"Current branch: {branch}")
            return branch
            
        except Exception as e:
            logger.error(f"Failed to get current branch: {e}")
            return None
    
    @staticmethod
    def cleanup_repository(repo_dir: Path) -> None:
        """
        Clean up cloned repository
        
        Args:
            repo_dir: Repository directory to remove
        """
        try:
            if repo_dir.exists():
                logger.info(f"Cleaning up repository: {repo_dir}")
                shutil.rmtree(repo_dir)
                logger.info("Repository cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup repository: {e}")

    @staticmethod
    def create_and_checkout_branch(
        repo_dir: Path, branch_name: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Create and checkout a new branch.

        Args:
            repo_dir: Repository directory
            branch_name: Name for the new branch

        Returns:
            Tuple of (success, error_message)
        """
        logger.info(f"Creating and checking out branch: {branch_name}")
        return GitUtilitiesService.run_git_command(
            ['checkout', '-b', branch_name], repo_dir
        )

    @staticmethod
    def push_branch(
        repo_dir: Path, branch_name: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Push a branch to the remote with upstream tracking.

        Args:
            repo_dir: Repository directory
            branch_name: Branch to push

        Returns:
            Tuple of (success, error_message)
        """
        logger.info(f"Pushing branch: {branch_name}")
        success, error = GitUtilitiesService.run_git_command(
            ['push', '-u', 'origin', branch_name], repo_dir
        )
        if success:
            logger.info(f"Branch {branch_name} pushed successfully")
        else:
            logger.error(f"Failed to push branch {branch_name}: {error}")
        return success, error

    @staticmethod
    def create_pull_request(
        repo_url: str,
        branch: str,
        base: str,
        title: str,
        body: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create a GitHub Pull Request using the ``gh`` CLI.

        Args:
            repo_url: Repository URL (HTTPS or SSH)
                      e.g. https://github.com/org/repo
                           git@github.com:org/repo.git
            branch: Head branch for the PR
            base: Base branch (e.g. main)
            title: PR title
            body: PR description body

        Returns:
            Tuple of (success, error_message, pr_url)
        """
        # Extract owner/repo from URL (supports both HTTPS and SSH formats)
        # SSH:   git@github.com:org/repo.git  -> org/repo
        # HTTPS: https://github.com/org/repo  -> org/repo
        repo_clean = repo_url.rstrip("/").removesuffix(".git")
        if repo_clean.startswith("git@"):
            # git@github.com:org/repo -> org/repo
            owner_repo = repo_clean.split(":")[-1]
        else:
            # https://github.com/org/repo -> org/repo
            parts = repo_clean.split("/")
            owner_repo = f"{parts[-2]}/{parts[-1]}"

        logger.info(f"Creating PR in {owner_repo}: {branch} -> {base}")
        try:
            result = subprocess.run(
                [
                    'gh', 'pr', 'create',
                    '--repo', owner_repo,
                    '--head', branch,
                    '--base', base,
                    '--title', title,
                    '--body', body,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error creating PR"
                logger.error(f"PR creation failed: {error_msg}")
                return False, error_msg, None

            pr_url = result.stdout.strip()
            logger.info(f"PR created: {pr_url}")
            return True, None, pr_url

        except subprocess.TimeoutExpired:
            error_msg = "gh pr create timed out"
            logger.error(error_msg)
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Failed to create PR: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None

    @staticmethod
    def create_repository_secrets(
        secrets_file: Path,
        owner: str,
        repo: str,
        overrides: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Create/update GitHub repository secrets from a secrets map file
        Uses GitHub CLI (gh) to set repository secrets
        
        Args:
            secrets_file: Path to secrets map file (key=value format)
            owner: Repository owner/organization
            repo: Repository name
            overrides: Optional dict of key-value pairs to override file values
            
        Returns:
            Tuple of (success, error_message)
            
        Example:
            secrets_file format:
                # Comment line
                API_KEY=my-secret-key
                DB_PASSWORD=/path/to/password/file
                SERVICE_URL=$SERVICE_ENDPOINT
        """
        try:
            if not secrets_file.exists():
                error_msg = f"Secrets file not found: {secrets_file}"
                logger.error(error_msg)
                return False, error_msg
            
            repo_full_name = f"{owner}/{repo}"
            logger.info(f"Setting secrets for repository: {repo_full_name}")
            
            overrides = overrides or {}
            secrets_set = 0
            
            # Read secrets from file
            with open(secrets_file, 'r') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value
                if '=' not in line:
                    logger.warning(f"Skipping invalid line {line_num}: {line}")
                    continue
                
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if not key:
                    logger.warning(f"Skipping line {line_num} with empty key")
                    continue
                
                # Apply override if exists
                if key in overrides:
                    value = overrides[key]
                    logger.debug(f"Using override for {key}")
                
                # Expand environment variables (e.g., $VAR or ${VAR})
                value = os.path.expandvars(value)
                
                # Check if value is a file path
                value_path = Path(value)
                if value_path.exists() and value_path.is_file():
                    logger.info(f"🔑 Setting secret from file: {key} ({value}) in {repo_full_name}")
                    # Read secret from file and pass via stdin
                    try:
                        with open(value_path, 'r') as secret_file:
                            secret_content = secret_file.read()
                        
                        result = subprocess.run(
                            ['gh', 'secret', 'set', key, '-R', repo_full_name],
                            input=secret_content,
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                    except Exception as e:
                        error_msg = f"Failed to read secret file {value}: {str(e)}"
                        logger.error(error_msg)
                        return False, error_msg
                else:
                    logger.info(f"🔑 Setting secret: {key} in {repo_full_name}")
                    result = subprocess.run(
                        ['gh', 'secret', 'set', key, '--body', value, '-R', repo_full_name],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                
                if result.returncode != 0:
                    error_msg = f"Failed to set secret '{key}': {result.stderr.strip()}"
                    logger.error(error_msg)
                    return False, error_msg
                
                secrets_set += 1
            
            logger.info(f"✅ Successfully set {secrets_set} secret(s) for {repo_full_name}")
            return True, None
            
        except subprocess.TimeoutExpired:
            error_msg = "GitHub secret set operation timed out"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Failed to create repository secrets: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    async def get_comment_by_id(
        comment_id: int, repo_name: Optional[str] = None
    ) -> dict:
        """
        Retrieve a specific GitHub issue comment by its ID.

        Args:
            comment_id: The unique comment ID.
            repo_name: Full repository name (``owner/repo``).
                       Falls back to ``GITOPS_REPO_URL`` from settings if not
                       provided.

        Returns:
            Dict with comment data from the GitHub API.

        Raises:
            HTTPException 400: If no repository could be determined.
            HTTPException 404: If the comment does not exist.
            HTTPException 502: If the GitHub API request fails.
        """
        if not repo_name:
            settings = get_settings()
            repo_url = settings.GITOPS_REPO_URL
            if not repo_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="repo_name is required when GITOPS_REPO_URL is not configured",
                )
            # Extract owner/repo from URL
            repo_clean = repo_url.rstrip("/").removesuffix(".git")
            if repo_clean.startswith("git@"):
                repo_name = repo_clean.split(":")[-1]
            else:
                parts = repo_clean.split("/")
                repo_name = f"{parts[-2]}/{parts[-1]}"

        settings = get_settings()
        url = f"https://api.github.com/repos/{repo_name}/issues/comments/{comment_id}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        }

        logger.info(f"Fetching comment {comment_id} from {repo_name}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=30)
        except httpx.HTTPError as exc:
            logger.error(f"GitHub API request failed for comment {comment_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to reach GitHub API: {exc}",
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comment {comment_id} not found in {repo_name}",
            )

        if response.status_code != 200:
            logger.error(
                f"GitHub API error for comment {comment_id}: "
                f"{response.status_code} {response.text}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API returned {response.status_code}",
            )

        return response.json()

    @staticmethod
    async def post_pr_comment(
        pr_number: int, comment: str, repo_name: Optional[str] = None
    ) -> dict:
        """
        Post a comment on a GitHub pull request.

        Args:
            pr_number: The pull request / issue number.
            comment: The comment body text.
            repo_name: Full repository name (``owner/repo``).
                       Falls back to ``GITOPS_REPO_URL`` from settings if not
                       provided.

        Returns:
            Dict with the created comment data from the GitHub API.

        Raises:
            HTTPException 400: If no repository could be determined.
            HTTPException 404: If the PR does not exist.
            HTTPException 502: If the GitHub API request fails.
        """
        if not repo_name:
            settings = get_settings()
            repo_url = settings.GITOPS_REPO_URL
            if not repo_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="repo_name is required when GITOPS_REPO_URL is not configured",
                )
            repo_clean = repo_url.rstrip("/").removesuffix(".git")
            if repo_clean.startswith("git@"):
                repo_name = repo_clean.split(":")[-1]
            else:
                parts = repo_clean.split("/")
                repo_name = f"{parts[-2]}/{parts[-1]}"

        settings = get_settings()
        url = f"https://api.github.com/repos/{repo_name}/issues/{pr_number}/comments"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        }
        payload = {"body": comment}

        logger.info(f"Posting comment on PR #{pr_number} in {repo_name}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, headers=headers, json=payload, timeout=30
                )
        except httpx.HTTPError as exc:
            logger.error(f"GitHub API request failed for PR #{pr_number}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to reach GitHub API: {exc}",
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PR #{pr_number} not found in {repo_name}",
            )

        if response.status_code not in (200, 201):
            logger.error(
                f"GitHub API error for PR #{pr_number}: "
                f"{response.status_code} {response.text}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API returned {response.status_code}",
            )

        logger.info(f"Comment posted on PR #{pr_number} in {repo_name}")
        return response.json()

    @staticmethod
    async def merge_pull_request(
        pull_number: int,
        commit_title: str,
        commit_message: str = "",
        merge_method: str = "squash",
        repo_name: Optional[str] = None,
    ) -> dict:
        """
        Merge a GitHub Pull Request via the GitHub REST API.

        PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge

        Args:
            pull_number: The pull request number to merge.
            commit_title: Title for the merge commit.
            commit_message: Extra detail appended to the merge commit message.
            merge_method: One of ``merge``, ``squash``, or ``rebase``
                          (default: ``squash``).
            repo_name: Full repository name (``owner/repo``).
                       Falls back to ``GITOPS_REPO_URL`` from settings if not
                       provided.

        Returns:
            Dict with the GitHub API response (sha, merged, message).

        Raises:
            HTTPException 400: If no repository could be determined or
                               merge_method is invalid.
            HTTPException 404: If the PR does not exist.
            HTTPException 405: If the PR is not mergeable.
            HTTPException 409: If the PR has a merge conflict.
            HTTPException 422: If GitHub rejected the request (validation).
            HTTPException 502: If the GitHub API request fails.
        """
        valid_merge_methods = {"merge", "squash", "rebase"}
        if merge_method not in valid_merge_methods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid merge_method '{merge_method}'. Must be one of: {sorted(valid_merge_methods)}",
            )

        if not repo_name:
            settings = get_settings()
            repo_url = settings.GITOPS_REPO_URL
            if not repo_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="repo_name is required when GITOPS_REPO_URL is not configured",
                )
            repo_clean = repo_url.rstrip("/").removesuffix(".git")
            if repo_clean.startswith("git@"):
                repo_name = repo_clean.split(":")[-1]
            else:
                parts = repo_clean.split("/")
                repo_name = f"{parts[-2]}/{parts[-1]}"

        settings = get_settings()
        url = f"https://api.github.com/repos/{repo_name}/pulls/{pull_number}/merge"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        }
        payload = {
            "commit_title": commit_title,
            "commit_message": commit_message,
            "merge_method": merge_method,
        }

        logger.info(
            f"Merging PR #{pull_number} in {repo_name} "
            f"(method={merge_method})"
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url, headers=headers, json=payload, timeout=30
                )
        except httpx.HTTPError as exc:
            logger.error(f"GitHub API request failed for PR #{pull_number} merge: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to reach GitHub API: {exc}",
            )

        status_handlers = {
            404: f"PR #{pull_number} not found in {repo_name}",
            405: f"PR #{pull_number} is not mergeable (already merged or checks pending)",
            409: f"PR #{pull_number} has a merge conflict and cannot be merged",
            422: f"GitHub rejected the merge request for PR #{pull_number}: {response.text}",
        }

        if response.status_code in status_handlers:
            detail = status_handlers[response.status_code]
            logger.error(detail)
            raise HTTPException(
                status_code=response.status_code,
                detail=detail,
            )

        if response.status_code != 200:
            logger.error(
                f"GitHub API error merging PR #{pull_number}: "
                f"{response.status_code} {response.text}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API returned {response.status_code}",
            )

        logger.info(f"PR #{pull_number} merged successfully in {repo_name}")
        return response.json()

    @staticmethod
    async def delete_branch(
        branch_name: str,
        repo_name: Optional[str] = None,
    ) -> dict:
        """
        Delete a branch from a GitHub repository via the GitHub REST API.

        DELETE /repos/{owner}/{repo}/git/refs/heads/{branch}

        Args:
            branch_name: The branch to delete (e.g. ``tf/client/dev/gcs/202501011200``).
            repo_name:   Full repository name (``owner/repo``).
                         Falls back to ``GITOPS_REPO_URL`` from settings if not
                         provided.

        Returns:
            Dict with ``branch`` and ``deleted: True`` on success.

        Raises:
            HTTPException 400: If no repository could be determined.
            HTTPException 404: If the branch does not exist.
            HTTPException 502: If the GitHub API request fails.
        """
        if not repo_name:
            settings = get_settings()
            repo_url = settings.GITOPS_REPO_URL
            if not repo_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="repo_name is required when GITOPS_REPO_URL is not configured",
                )
            repo_clean = repo_url.rstrip("/").removesuffix(".git")
            if repo_clean.startswith("git@"):
                repo_name = repo_clean.split(":")[-1]
            else:
                parts = repo_clean.split("/")
                repo_name = f"{parts[-2]}/{parts[-1]}"

        settings = get_settings()
        url = f"https://api.github.com/repos/{repo_name}/git/refs/heads/{branch_name}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        }

        logger.info(f"Deleting branch '{branch_name}' from {repo_name}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=headers, timeout=30)
        except httpx.HTTPError as exc:
            logger.error(f"GitHub API request failed deleting branch '{branch_name}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to reach GitHub API: {exc}",
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Branch '{branch_name}' not found in {repo_name}",
            )

        # GitHub returns 204 No Content on successful branch deletion
        if response.status_code != 204:
            logger.error(
                f"GitHub API error deleting branch '{branch_name}': "
                f"{response.status_code} {response.text}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API returned {response.status_code}",
            )

        logger.info(f"Branch '{branch_name}' deleted successfully from {repo_name}")
        return {"branch": branch_name, "deleted": True}

    @staticmethod
    async def close_pull_request(
        pull_number: int,
        repo_name: Optional[str] = None,
    ) -> dict:
        """
        Close a GitHub Pull Request without merging via the GitHub REST API.

        PATCH /repos/{owner}/{repo}/pulls/{pull_number}
        Body: {"state": "closed"}

        Args:
            pull_number: The pull request number to close.
            repo_name:   Full repository name (``owner/repo``).
                         Falls back to ``GITOPS_REPO_URL`` from settings if not
                         provided.

        Returns:
            Dict with ``pull_number``, ``state``, and ``closed: True``.

        Raises:
            HTTPException 400: If no repository could be determined.
            HTTPException 404: If the PR does not exist.
            HTTPException 422: If GitHub rejected the request (e.g. already closed).
            HTTPException 502: If the GitHub API request fails.
        """
        if not repo_name:
            settings = get_settings()
            repo_url = settings.GITOPS_REPO_URL
            if not repo_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="repo_name is required when GITOPS_REPO_URL is not configured",
                )
            repo_clean = repo_url.rstrip("/").removesuffix(".git")
            if repo_clean.startswith("git@"):
                repo_name = repo_clean.split(":")[-1]
            else:
                parts = repo_clean.split("/")
                repo_name = f"{parts[-2]}/{parts[-1]}"

        settings = get_settings()
        url = f"https://api.github.com/repos/{repo_name}/pulls/{pull_number}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        }
        payload = {"state": "closed"}

        logger.info(f"Closing PR #{pull_number} in {repo_name}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url, headers=headers, json=payload, timeout=30
                )
        except httpx.HTTPError as exc:
            logger.error(f"GitHub API request failed closing PR #{pull_number}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to reach GitHub API: {exc}",
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PR #{pull_number} not found in {repo_name}",
            )

        if response.status_code == 422:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"GitHub rejected close request for PR #{pull_number}: {response.text}",
            )

        if response.status_code != 200:
            logger.error(
                f"GitHub API error closing PR #{pull_number}: "
                f"{response.status_code} {response.text}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API returned {response.status_code}",
            )

        data = response.json()
        logger.info(f"PR #{pull_number} closed successfully in {repo_name}")
        return {
            "pull_number": pull_number,
            "state": data.get("state"),
            "closed": True,
        }


# Create singleton instance
git_service = GitUtilitiesService()