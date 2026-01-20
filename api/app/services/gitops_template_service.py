"""
GitOps Template Processing Service
Handles template file processing with variable substitution
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from app.core.logging_config import logger
from app.core.config import get_settings


class GitOpsTemplateService:
    """
    Service for processing GitOps template files

    Reads template files, performs variable substitution,
    and outputs processed files maintaining directory structure.
    """

    # Template variable placeholders
    PLACEHOLDER_MICROSERVICE_NAME = "{{MICRO_SERVICE_NAME}}"
    PLACEHOLDER_MICROSERVICE_URL = "{{MICRO_SERVICE_URL}}"
    PLACEHOLDER_CONTAINER_PORT = "{{CONTAINER_PORT}}"
    PLACEHOLDER_DOMAIN_NAME = "{{DOMAIN_NAME}}"
    PLACEHOLDER_ENVIRONMENT = "{{ENVIRONMENT}}"
    PLACEHOLDER_GIT_REPO_NAME = "{{GIT_REPO_NAME}}"
    PLACEHOLDER_GIT_BRANCH = "{{GIT_BRANCH}}"
    PLACEHOLDER_GIT_SECRET = "{{GIT_SECRET}}"
    PLACEHOLDER_ARGOCD_APP_NAME = "{{ARGOCD_APP_NAME}}"
    PLACEHOLDER_GITOPS_REPO_URL = "{{GITOPS_REPO_URL}}"
    PLACEHOLDER_ENVIRONMENT_VARIABLES = "{{ENVIRONMENT_VARIABLES}}"
    PLACEHOLDER_ENVIRONMENT_VARIABLES_YAML = "{{ENVIRONMENT_VARIABLES_YAML}}"
    PLACEHOLDER_ENVIRONMENT_VARIABLES_CONFIGMAP = "{{ENVIRONMENT_VARIABLES_CONFIGMAP}}"

    def __init__(
        self,
        template_dir: Optional[Path] = None,
        output_base_dir: Optional[Path] = None
    ):
        """
        Initialize the template service

        Args:
            template_dir: Path to template directory (default: template/git-ops)
            output_base_dir: Base path for output (default: UPLOAD_DIR/session_id/git-ops)
        """
        settings = get_settings()

        # Generate session ID for unique output directory
        self.session_id = str(uuid.uuid4())

        # Set default paths relative to project root
        project_root = Path(__file__).parent.parent.parent
        # self.template_dir = template_dir or project_root / "app" / "templates" / "git-ops"
        self.template_dir = template_dir or project_root / "app" / "templates" 
        self.output_base_dir = output_base_dir or project_root / "app" / "temp" / self.session_id 

        # Ensure output directory exists
        self.output_base_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"GitOpsTemplateService initialized")
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"Template directory: {self.template_dir}")
        logger.info(f"Output base directory: {self.output_base_dir}")

    def validate_template_directory(self) -> Tuple[bool, Optional[str]]:
        """
        Validate that template directory exists and contains files

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.template_dir.exists():
            return False, f"Template directory not found: {self.template_dir}"

        if not self.template_dir.is_dir():
            return False, f"Template path is not a directory: {self.template_dir}"

        # Check if directory has any files
        files = list(self.template_dir.rglob("*"))
        if not any(f.is_file() for f in files):
            return False, f"Template directory is empty: {self.template_dir}"

        return True, None

    def get_template_files(self) -> List[Path]:
        """
        Get all files from template directory recursively

        Returns:
            List of file paths
        """
        files = []
        for file_path in self.template_dir.rglob("*"):
            if file_path.is_file():
                files.append(file_path)
                logger.debug(f"Found template file: {file_path}")

        logger.info(f"Found {len(files)} template files")
        return files

    def parse_env_content(self, env_content: Optional[str]) -> Dict[str, str]:
        """
        Parse environment variables from .env file content
        (Same logic as ConfigMapService.parse_env_content)

        Args:
            env_content: Content of .env file as string (KEY=VALUE pairs)

        Returns:
            Dictionary of environment variables
        """
        if not env_content:
            return {}

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

    def format_env_vars_yaml(self, env_vars: Dict[str, str], indent: int = 2) -> str:
        """
        Format environment variables as YAML key-value pairs

        Args:
            env_vars: Dictionary of environment variables
            indent: Number of spaces for indentation

        Returns:
            YAML formatted string
        """
        if not env_vars:
            return ""

        indent_str = " " * indent
        lines = []
        for key, value in env_vars.items():
            # Quote values that need it
            if any(c in str(value) for c in [' ', ':', '#', '{', '}', '[', ']', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`']):
                value = f'"{value}"'
            lines.append(f"{indent_str}{key}: {value}")

        return '\n'.join(lines)

    def format_env_vars_configmap(self, env_vars: Dict[str, str], indent: int = 2) -> str:
        """
        Format environment variables for Kubernetes ConfigMap data section

        Args:
            env_vars: Dictionary of environment variables
            indent: Number of spaces for indentation

        Returns:
            ConfigMap data section formatted string
        """
        if not env_vars:
            return ""

        indent_str = " " * indent
        lines = []
        for key, value in env_vars.items():
            # Use Helm template syntax for ConfigMap
            lines.append(f"{indent_str}{key}: {{{{ .Values.config.{key} | quote }}}}")

        return '\n'.join(lines)

    def format_env_vars_values_yaml(self, env_vars: Dict[str, str], indent: int = 2) -> str:
        """
        Format environment variables for values.yaml config section

        Args:
            env_vars: Dictionary of environment variables
            indent: Number of spaces for indentation

        Returns:
            values.yaml config section formatted string
        """
        if not env_vars:
            return ""

        indent_str = " " * indent
        lines = []
        for key, value in env_vars.items():
            # Quote string values
            lines.append(f"{indent_str}{key}: \"{value}\"")

        return '\n'.join(lines)

    def build_replacement_map(
        self,
        microservice_name: str,
        microservice_url: str,
        container_port: int,
        domain_name: str,
        environment: str,
        git_repo_name: str,
        git_branch: str,
        git_secret: str,
        argocd_app_name: str,
        gitops_repo_url: str,
        env_content: Optional[str] = None
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Build the replacement map for template processing

        Args:
            microservice_name: Name of the microservice
            microservice_url: URL/path for the microservice
            container_port: Container port number
            domain_name: Domain name for ingress
            environment: Target environment
            git_repo_name: Git repository name
            git_branch: Git branch
            argocd_app_name: ArgoCD application name
            gitops_repo_url: GitOps repository URL
            env_content: Optional .env file content (KEY=VALUE pairs)

        Returns:
            Tuple of (replacements dict, parsed env_vars dict)
        """
        # Parse environment variables from env_content (same as ConfigMap)
        env_vars = self.parse_env_content(env_content)

        replacements = {
            self.PLACEHOLDER_MICROSERVICE_NAME: microservice_name,
            self.PLACEHOLDER_MICROSERVICE_URL: microservice_url,
            self.PLACEHOLDER_CONTAINER_PORT: str(container_port),
            self.PLACEHOLDER_DOMAIN_NAME: domain_name,
            self.PLACEHOLDER_ENVIRONMENT: environment,
            self.PLACEHOLDER_GIT_REPO_NAME: git_repo_name,
            self.PLACEHOLDER_GIT_BRANCH: git_branch,
            self.PLACEHOLDER_GIT_SECRET: git_secret,
            self.PLACEHOLDER_ARGOCD_APP_NAME: argocd_app_name,
            self.PLACEHOLDER_GITOPS_REPO_URL: gitops_repo_url,
        }

        # Add environment variable formatted placeholders
        if env_vars:
            # YAML format for values.yaml config section
            replacements[self.PLACEHOLDER_ENVIRONMENT_VARIABLES_YAML] = self.format_env_vars_values_yaml(env_vars)
            # ConfigMap template format
            replacements[self.PLACEHOLDER_ENVIRONMENT_VARIABLES_CONFIGMAP] = self.format_env_vars_configmap(env_vars)
            # Simple YAML format
            replacements[self.PLACEHOLDER_ENVIRONMENT_VARIABLES] = self.format_env_vars_yaml(env_vars)

            # Also add individual env vars as placeholders (e.g., {{LOG_LEVEL}})
            for key, value in env_vars.items():
                placeholder = f"{{{{{key}}}}}"
                replacements[placeholder] = value

        logger.info(f"Built replacement map with {len(replacements)} variables")
        logger.info(f"Parsed {len(env_vars)} environment variables from env_content")
        return replacements, env_vars

    def process_file_content(
        self,
        content: str,
        replacements: Dict[str, str]
    ) -> Tuple[str, int]:
        """
        Process file content with variable substitution

        Args:
            content: Original file content
            replacements: Dictionary of placeholder -> value mappings

        Returns:
            Tuple of (processed_content, replacement_count)
        """
        processed_content = content
        total_replacements = 0

        for placeholder, value in replacements.items():
            count = processed_content.count(placeholder)
            if count > 0:
                processed_content = processed_content.replace(placeholder, value)
                total_replacements += count
                logger.debug(f"Replaced {count} occurrences of {placeholder}")

        return processed_content, total_replacements

    def process_template(
        self,
        microservice_name: str,
        microservice_url: str,
        container_port: int,
        domain_name: str,
        environment: str,
        git_repo_name: str,
        git_branch: str,
        git_secret: str,
        argocd_app_name: str,
        gitops_repo_url: str,
        env_content: Optional[str] = None
    ) -> Dict:
        """
        Process all template files with variable substitution

        Args:
            microservice_name: Name of the microservice
            microservice_url: URL/path for the microservice
            container_port: Container port number
            domain_name: Domain name for ingress
            environment: Target environment
            git_repo_name: Git repository name
            git_branch: Git branch
            git_secret: Github Secret Key
            argocd_app_name: ArgoCD application name
            gitops_repo_url: GitOps repository URL
            env_content: Optional .env file content (KEY=VALUE pairs, same as ConfigMap)

        Returns:
            Dictionary with processing results
        """
        logger.info(f"=== Starting GitOps Template Processing ===")
        logger.info(f"Microservice: {microservice_name}")
        logger.info(f"Environment: {environment}")

        # Validate template directory
        is_valid, error = self.validate_template_directory()
        if not is_valid:
            raise ValueError(error)

        # Output structure: output_base_dir/git-ops/microservice_name/ (helm chart)
        #                   output_base_dir/github/microservice_name/ (github workflows)
        # Clean up any existing output for this microservice
        for template_folder in ['git-ops', 'github']:
            microservice_output = self.output_base_dir / template_folder / microservice_name
            if microservice_output.exists():
                logger.info(f"Removing existing output directory: {microservice_output}")
                shutil.rmtree(microservice_output)

        logger.info(f"Output base directory: {self.output_base_dir}")

        # Build replacement map
        replacements, env_vars = self.build_replacement_map(
            microservice_name=microservice_name,
            microservice_url=microservice_url,
            container_port=container_port,
            domain_name=domain_name,
            environment=environment,
            git_repo_name=git_repo_name,
            git_branch=git_branch,
            git_secret=git_secret,
            argocd_app_name=argocd_app_name,
            gitops_repo_url=gitops_repo_url,
            env_content=env_content
        )

        # Get template files
        template_files = self.get_template_files()

        # Process each file
        processed_files = []
        for template_file in template_files:
            try:
                # Calculate relative path to maintain structure
                # relative_path is like: git-ops/values.yaml or github/workflows.yaml
                relative_path = template_file.relative_to(self.template_dir)

                # Insert microservice_name after the template folder (git-ops or github)
                # Structure: output_base_dir/git-ops/microservice_name/values.yaml
                path_parts = relative_path.parts
                if len(path_parts) >= 1:
                    template_folder = path_parts[0]  # git-ops or github
                    rest_of_path = Path(*path_parts[1:]) if len(path_parts) > 1 else Path("")
                    output_file = self.output_base_dir / template_folder / microservice_name / rest_of_path
                else:
                    output_file = self.output_base_dir / microservice_name / relative_path

                # Create parent directories if needed
                output_file.parent.mkdir(parents=True, exist_ok=True)

                # Read template content
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Process content
                processed_content, replacement_count = self.process_file_content(
                    content, replacements
                )

                # Write processed content
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(processed_content)

                processed_files.append({
                    'source_path': str(template_file),
                    'output_path': str(output_file),
                    'replacements_made': replacement_count
                })

                logger.info(f"Processed: {relative_path} ({replacement_count} replacements)")

            except UnicodeDecodeError:
                # Binary file - copy without processing
                logger.warning(f"Binary file detected, copying without processing: {template_file}")
                shutil.copy2(template_file, output_file)
                processed_files.append({
                    'source_path': str(template_file),
                    'output_path': str(output_file),
                    'replacements_made': 0
                })

            except Exception as e:
                logger.error(f"Error processing file {template_file}: {e}")
                raise

        logger.info(f"=== GitOps Template Processing Complete ===")
        logger.info(f"Total files processed: {len(processed_files)}")

        # Return human-readable replacement map (without {{ }})
        readable_replacements = {
            k.replace("{{", "").replace("}}", ""): v
            for k, v in replacements.items()
            # Exclude the formatted env var blocks from the simple variables list
            if k not in [
                self.PLACEHOLDER_ENVIRONMENT_VARIABLES,
                self.PLACEHOLDER_ENVIRONMENT_VARIABLES_YAML,
                self.PLACEHOLDER_ENVIRONMENT_VARIABLES_CONFIGMAP
            ]
        }

        return {
            'output_directory': str(self.output_base_dir),
            'processed_files': processed_files,
            'total_files_processed': len(processed_files),
            'template_variables': readable_replacements,
            'environment_variables': env_vars
        }

    def cleanup_output(self, microservice_name: str) -> None:
        """
        Clean up output directory for a microservice

        Args:
            microservice_name: Name of the microservice
        """
        output_dir = self.output_base_dir / microservice_name
        if output_dir.exists():
            logger.info(f"Cleaning up output directory: {output_dir}")
            shutil.rmtree(output_dir)
            logger.info("Cleanup complete")


# Singleton instance
gitops_template_service = GitOpsTemplateService()
