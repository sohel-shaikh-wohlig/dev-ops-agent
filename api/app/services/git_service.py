"""
Git Utilities Service
Handles Git operations: clone, pull, commit, push
Based on original script's git functionality
"""
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple, List
from app.core.logging_config import logger


class GitUtilitiesService:
    """
    Service for Git operations
    Mirrors the original script's git functionality
    """
    
    @staticmethod
    def clone_repository(
        git_url: str,
        target_dir: Path,
        branch: str = "main",
        depth: int = 1
    ) -> Tuple[bool, Optional[str]]:
        """
        Clone a Git repository
        
        Args:
            git_url: Git repository URL
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
            
            logger.info(f"Cloning repository: {git_url} to {target_dir}")
            
            # Try to clone with specific branch
            result = subprocess.run(
                ['git', 'clone', '--branch', branch, '--depth', str(depth), git_url, str(target_dir)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                # Try without branch specification (might not exist)
                logger.warning(f"Branch {branch} not found, trying default branch")
                result = subprocess.run(
                    ['git', 'clone', '--depth', str(depth), git_url, str(target_dir)],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
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
            error_msg = f"Git command failed: git {' '.join(args)}\nError: {e.stderr}"
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
        commit_message: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Commit changes to repository
        
        Args:
            repo_dir: Repository directory
            commit_message: Commit message
            
        Returns:
            Tuple of (success, error_message, commit_hash)
        """
        logger.info(f"Committing changes with message: {commit_message}")
        
        success, error = GitUtilitiesService.run_git_command(
            ['commit', '-m', commit_message],
            repo_dir
        )
        
        if not success:
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


# Create singleton instance
git_service = GitUtilitiesService()