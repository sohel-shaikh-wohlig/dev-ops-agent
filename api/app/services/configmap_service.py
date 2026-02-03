import re
import uuid
import shutil
import subprocess
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from app.core.logging_config import logger
from app.core.config import get_settings

# Keywords that indicate sensitive values (case-insensitive)
# Matches as standalone words: SECRET, KEY, TOKEN
# Valid: API_KEY, SECRET_VALUE, TOKEN_, _KEY
# Invalid: KEYCLOAK, MONKEY, BUCKET (keyword embedded in another word)
SENSITIVE_KEYWORDS = ('SECRET', 'KEY', 'TOKEN', 'PASSWORD')

# Regex pattern to match keywords as standalone words (not embedded in other words)
# Matches: start/underscore + KEYWORD + end/underscore
# Example: API_KEY ✓, _SECRET_ ✓, TOKEN ✓, KEYCLOAK ✗, MONKEY ✗
SENSITIVE_PATTERN = re.compile(
    r'(^|_)(' + '|'.join(SENSITIVE_KEYWORDS) + r')(_|$)',
    re.IGNORECASE
)


def mask_sensitive_values(config: Dict[str, str]) -> Dict[str, str]:
    """
    Mask sensitive values in a configuration dictionary.

    Scans all keys for sensitive keywords (SECRET, KEY, TOKEN) as standalone words.
    Keywords must be separated by underscores or at string boundaries.

    Valid matches: API_KEY, SECRET_VALUE, TOKEN, _KEY_, MY_SECRET
    Not matched: KEYCLOAK, MONKEY, BUCKET (keyword embedded in word)

    For matching keys, masks the value to show only the last 5 characters
    with a '***' prefix.

    Args:
        config: Dictionary of configuration key-value pairs

    Returns:
        Dictionary with sensitive values masked

    Example:
        Input:  {'API_TOKEN': 'my-super-secret-12345', 'KEYCLOAK_URL': 'https://...'}
        Output: {'API_TOKEN': '***12345', 'KEYCLOAK_URL': 'https://...'}
    """
    masked_config = {}

    for key, value in config.items():
        # Check if key contains any sensitive keyword as a standalone word
        # Uses regex to ensure keyword is not part of another word (e.g., KEYCLOAK)
        is_sensitive = bool(SENSITIVE_PATTERN.search(key))

        if is_sensitive and value:
            # If value is 5 characters or less, display without masking
            if len(value) <= 5:
                masked_config[key] = value
            else:
                # Show only last 5 characters with placeholder prefix
                masked_config[key] = f"***{value[-5:]}"
        else:
            masked_config[key] = value

    # Return config sorted alphabetically by key
    return dict(sorted(masked_config.items(), key=lambda x: x[0].lower()))


def get_values_from_gitops(microservice_name: str, env: str) -> dict:
    """
    Fetch the 'config' block from a values.yaml file in a remote GitOps repository.

    Args:
        microservice_name: Name of the microservice (used as directory name)
        env: Environment name, used as the Git branch name (e.g., 'development', 'staging', 'production')

    Returns:
        Dictionary containing the 'config' block from values.yaml, or empty dict if not present

    Raises:
        ValueError: If the branch does not exist or values.yaml file is not found
        Exception: If Git clone or file read operations fail
    """
    settings = get_settings()
    session_id = str(uuid.uuid4())
    repo_dir = settings.UPLOAD_DIR / session_id / "repo"

    # Get GitOps URL from environment settings
    gitops_url = settings.GITOPS_REPO_URL
    if not gitops_url:
        raise ValueError(
            "GITOPS_REPO_URL is not configured. "
            "Please set GITOPS_REPO_URL in your .env file."
        )

    try:
        logger.info(f"=== Fetching values from GitOps repository ===")
        logger.info(f"Microservice: {microservice_name}")
        logger.info(f"Branch (env): {env}")
        logger.info(f"Cloning repository from {gitops_url} (branch: {env})...")

        # Remove target directory if it exists
        if repo_dir.exists():
            shutil.rmtree(repo_dir)

        # Create parent directory
        repo_dir.parent.mkdir(parents=True, exist_ok=True)

        # Clone with specific branch - fail if branch doesn't exist
        result = subprocess.run(
            ['git', 'clone', '--branch', env, '--depth', '1', gitops_url, str(repo_dir)],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            error_msg = result.stderr or "Unknown error during clone"
            # Check for branch not found
            if "Remote branch" in error_msg and "not found" in error_msg:
                raise ValueError(
                    f"Branch '{env}' does not exist in the GitOps repository. "
                    f"Available branches may include: development, staging, production"
                )
            # Check for authentication/connection errors
            if "Authentication failed" in error_msg or "could not read Username" in error_msg:
                raise Exception(f"Git authentication failed: {error_msg}")
            if "Could not resolve host" in error_msg or "unable to access" in error_msg:
                raise Exception(f"Git connection error: {error_msg}")
            raise Exception(f"Failed to clone repository: {error_msg}")

        logger.info(f"Repository cloned successfully to {repo_dir}")

        # Determine the config file path based on microservice name
        if microservice_name.endswith('frontend'):
            # Frontend services use a different directory structure with data.env
            config_dir = f"{microservice_name}-env"
            config_file = repo_dir / config_dir / "data.env"
            is_frontend = True
            logger.info(f"Frontend service detected, looking for data.env at: {config_file}")
        else:
            # Default path: {microservice_name}/values.yaml
            config_file = repo_dir / microservice_name / "values.yaml"
            is_frontend = False
            logger.info(f"Looking for values.yaml at: {config_file}")

        if not config_file.exists():
            if is_frontend:
                raise ValueError(
                    f"data.env not found at '{microservice_name}-frontend-env/data.env' in the repository. "
                    f"Please verify the microservice name and repository structure."
                )
            else:
                raise ValueError(
                    f"values.yaml not found at '{microservice_name}/values.yaml' in the repository. "
                    f"Please verify the microservice name and repository structure."
                )

        # Parse the config file based on type
        if is_frontend:
            # Parse data.env file (KEY=VALUE format)
            logger.info("Parsing data.env...")
            config_block = {}
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        config_block[key] = value
        else:
            # Parse YAML file
            logger.info("Parsing values.yaml...")
            with open(config_file, 'r') as f:
                values_data = yaml.safe_load(f)

            if values_data is None:
                logger.warning("values.yaml is empty")
                return {}

            # Extract only the 'config' block
            config_block = values_data.get('config', {})

        if not config_block:
            config_source = "data.env" if is_frontend else "values.yaml"
            logger.info(f"No config entries found in {config_source}, returning empty dict")
            return {}

        # Convert all values to strings (handles bool, int, float, etc.)
        config_as_strings = {
            key: str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in config_block.items()
        }

        logger.info(f"Found 'config' block with {len(config_as_strings)} entries")

        return config_as_strings

    except ValueError:
        # Re-raise ValueError as-is (descriptive errors for branch/file not found)
        raise
    except Exception as e:
        logger.error(f"Failed to fetch values from GitOps: {str(e)}", exc_info=True)
        raise
    finally:
        # Always clean up temporary directory
        if repo_dir.exists():
            logger.info(f"Cleaning up temporary directory: {repo_dir.parent}")
            try:
                shutil.rmtree(repo_dir.parent)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temporary directory: {cleanup_error}")


class ConfigMapService:
    """
    Service for updating GitOps ConfigMap files
    """
    
    def __init__(self, microservice_path: Path):
        """
        Initialize the configuration service
        
        Args:
            microservice_path: Path to the microservice directory
        """
        self.microservice_path = Path(microservice_path)
        self.values_file = self.microservice_path / "values.yaml"
        self.configmap_file = self.microservice_path / "templates" / "configmap.yaml"
        self.changes: List[Dict] = []
        
        logger.info(f"Initialized ConfigMapService for {microservice_path}")
    
    def validate_structure(self) -> Tuple[bool, Optional[str]]:
        """
        Validate that required files exist
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.values_file.exists():
            return False, f"values.yaml not found at {self.values_file}"
        
        if not self.configmap_file.exists():
            # Check if templates directory exists
            templates_dir = self.microservice_path / "templates"
            if not templates_dir.exists():
                return False, f"templates directory not found at {templates_dir}"
            return False, f"configmap.yaml not found at {self.configmap_file}"
        
        return True, None
    
    def parse_env_content(self, env_content: str) -> Dict[str, str]:
        """
        Parse environment variables from .env file content
        (Original: load_env_file)
        
        Args:
            env_content: Content of .env file as string
            
        Returns:
            Dictionary of environment variables
        """
        env_vars = {}
        
        for line_num, line in enumerate(env_content.split('\n'), 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                env_vars[key] = value
                logger.debug(f"Parsed env var: {key}={value}")
            else:
                logger.warning(f"Skipping invalid line {line_num}: {line}")
        
        logger.info(f"Loaded {len(env_vars)} variables from env content")
        return env_vars
    
    def load_values_yaml(self) -> Dict:
        """
        Load values.yaml file
        
        Returns:
            Parsed YAML content as dictionary
        """
        try:
            with open(self.values_file, 'r') as f:
                data = yaml.safe_load(f)
            logger.info(f"Loaded values.yaml from {self.values_file}")
            return data
        except Exception as e:
            logger.error(f"Failed to load values.yaml: {e}")
            raise
    
    def save_values_yaml(self, data: Dict) -> None:
        """
        Save values.yaml file
        
        Args:
            data: Dictionary to save as YAML
        """
        try:
            with open(self.values_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved values.yaml to {self.values_file}")
        except Exception as e:
            logger.error(f"Failed to save values.yaml: {e}")
            raise
    
    def update_values_yaml(self, env_vars: Dict[str, str], values_data: Dict) -> Dict:
        """
        Update values.yaml with new environment variables.
        Implements change detection to avoid redundant updates.

        Args:
            env_vars: Environment variables to update
            values_data: Current values.yaml content

        Returns:
            Updated values.yaml content

        Change Detection:
            - ADD: Key does not exist, will be inserted
            - UPDATE: Key exists but value is different
            - UNCHANGED: Key exists and value is identical (no update performed)
        """
        if 'config' not in values_data:
            values_data['config'] = {}

        for key, value in env_vars.items():
            old_value = values_data['config'].get(key)

            # Convert old_value to string for comparison (handles bool, int, etc.)
            old_value_str = None
            if old_value is not None:
                old_value_str = str(old_value).lower() if isinstance(old_value, bool) else str(old_value)

            if old_value is None:
                # Key does not exist - ADD
                self.changes.append({
                    'file': 'values.yaml',
                    'type': 'ADD',
                    'key': key,
                    'old': None,
                    'new': value
                })
                logger.info(f"[ADD] New key in values.yaml: {key}={value}")
                values_data['config'][key] = value

            elif old_value_str != value:
                # Key exists but value is different - UPDATE
                self.changes.append({
                    'file': 'values.yaml',
                    'type': 'UPDATE',
                    'key': key,
                    'old': old_value_str,
                    'new': value
                })
                logger.info(f"[UPDATE] Changed value in values.yaml: {key} = '{old_value_str}' -> '{value}'")
                values_data['config'][key] = value

            else:
                # Key exists and value is identical - UNCHANGED
                self.changes.append({
                    'file': 'values.yaml',
                    'type': 'UNCHANGED',
                    'key': key,
                    'old': old_value_str,
                    'new': value
                })
                logger.debug(f"[UNCHANGED] No change for key in values.yaml: {key}={value}")

        return values_data
    
    def update_configmap_template(self, env_vars: Dict[str, str]) -> str:
        """
        Update configmap.yaml template with new variables.
        Implements change detection to avoid redundant updates.

        Args:
            env_vars: Environment variables to update

        Returns:
            Updated configmap.yaml content as string

        Change Detection:
            - ADD: Key does not exist in template, will be inserted
            - UNCHANGED: Key already exists in template (template format is standard)
        """
        with open(self.configmap_file, 'r') as f:
            content = f.read()

        # Parse existing data section
        data_section_match = re.search(r'\bdata:\s*\n((?:  \w+:.*\n)*)', content)

        if not data_section_match:
            raise ValueError("Could not find 'data:' section in configmap.yaml")

        existing_keys = set()
        data_lines = data_section_match.group(1).split('\n')

        for line in data_lines:
            if line.strip():
                key_match = re.match(r'\s*(\w+):', line)
                if key_match:
                    existing_keys.add(key_match.group(1))

        # Track changes for configmap
        new_lines = []
        updated_content = content

        for key in env_vars.keys():
            template_value = f'{{{{ .Values.config.{key} | quote }}}}'
            new_line = f'  {key}: {template_value}'

            if key in existing_keys:
                # Key already exists in configmap template - UNCHANGED
                # (Template format is standardized, no need to update)
                self.changes.append({
                    'file': 'configmap.yaml',
                    'type': 'UNCHANGED',
                    'key': key,
                    'old': template_value,
                    'new': template_value
                })
                logger.debug(f"[UNCHANGED] Key already exists in configmap.yaml: {key}")
            else:
                # Add new line - ADD
                self.changes.append({
                    'file': 'configmap.yaml',
                    'type': 'ADD',
                    'key': key,
                    'old': None,
                    'new': template_value
                })
                logger.info(f"[ADD] New entry in configmap.yaml: {key}")
                new_lines.append(new_line)

        # Append new lines to data section
        if new_lines:
            data_end = data_section_match.end()
            updated_content = (
                updated_content[:data_end] +
                '\n'.join(new_lines) + '\n' +
                updated_content[data_end:]
            )

        return updated_content
    
    def preview_changes(self, env_vars: Dict[str, str]) -> List[Dict]:
        """
        Preview changes without applying them
        
        Args:
            env_vars: Environment variables to preview
            
        Returns:
            List of changes that would be made
        """
        self.changes = []  # Reset changes
        
        # Validate structure
        is_valid, error_msg = self.validate_structure()
        if not is_valid:
            raise ValueError(error_msg)
        
        # Load current values
        values_data = self.load_values_yaml()
        
        # Generate preview changes (without saving)
        self.update_values_yaml(env_vars, values_data)
        self.update_configmap_template(env_vars)
        
        logger.info(f"Generated preview: {len(self.changes)} changes")
        return self.changes
    
    def apply_changes(self, env_vars: Dict[str, str]) -> Tuple[List[Dict], bool]:
        """
        Apply changes to configuration files with change detection.
        Only writes files if there are actual changes (ADD or UPDATE).

        Args:
            env_vars: Environment variables to apply

        Returns:
            Tuple of (list of all changes, bool indicating if files were modified)

        Change Detection:
            - If all keys are UNCHANGED, files are not modified
            - Returns has_changes=False to signal Git commit should be skipped
        """
        self.changes = []  # Reset changes

        # Validate structure
        is_valid, error_msg = self.validate_structure()
        if not is_valid:
            raise ValueError(error_msg)

        # Load current values.yaml
        values_data = self.load_values_yaml()

        # Detect changes in values.yaml (populates self.changes)
        updated_values = self.update_values_yaml(env_vars, values_data)

        # Detect changes in configmap.yaml (adds to self.changes)
        updated_configmap = self.update_configmap_template(env_vars)

        # Check if there are any actual changes
        if self.has_actual_changes():
            # Save values.yaml only if there are actual changes
            self.save_values_yaml(updated_values)

            # Save configmap.yaml only if there are actual changes
            with open(self.configmap_file, 'w') as f:
                f.write(updated_configmap)

            actual_count = len(self.get_actual_changes())
            unchanged_count = len(self.get_unchanged_entries())
            logger.info(f"Applied {actual_count} changes ({unchanged_count} unchanged)")
            return self.changes, True
        else:
            unchanged_count = len(self.get_unchanged_entries())
            logger.info(f"No changes to apply - all {unchanged_count} entries are unchanged")
            return self.changes, False
    
    def get_changes_summary(self) -> Dict[str, int]:
        """
        Get summary of changes including unchanged count.

        Returns:
            Dictionary with change counts by type and file
        """
        summary = {
            'total_entries': len(self.changes),
            'values_yaml_changes': len([c for c in self.changes if c['file'] == 'values.yaml' and c['type'] != 'UNCHANGED']),
            'configmap_yaml_changes': len([c for c in self.changes if c['file'] == 'configmap.yaml' and c['type'] != 'UNCHANGED']),
            'additions': len([c for c in self.changes if c['type'] == 'ADD']),
            'updates': len([c for c in self.changes if c['type'] == 'UPDATE']),
            'unchanged': len([c for c in self.changes if c['type'] == 'UNCHANGED']),
            'actual_changes': len([c for c in self.changes if c['type'] in ('ADD', 'UPDATE')])
        }
        return summary

    def has_actual_changes(self) -> bool:
        """
        Check if there are any actual changes (ADD or UPDATE).
        Used to determine if Git commit/push should be performed.

        Returns:
            True if there are ADD or UPDATE changes, False if all are UNCHANGED
        """
        return any(c['type'] in ('ADD', 'UPDATE') for c in self.changes)

    def get_actual_changes(self) -> List[Dict]:
        """
        Get only the actual changes (ADD or UPDATE), excluding UNCHANGED.

        Returns:
            List of changes that are ADD or UPDATE type
        """
        return [c for c in self.changes if c['type'] in ('ADD', 'UPDATE')]

    def get_unchanged_entries(self) -> List[Dict]:
        """
        Get all unchanged entries.

        Returns:
            List of entries that are UNCHANGED type
        """
        return [c for c in self.changes if c['type'] == 'UNCHANGED']