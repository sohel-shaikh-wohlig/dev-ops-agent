"""
GitOps Template Processing Service
Handles template file processing with variable substitution
"""

import os
import shutil
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
    PLACEHOLDER_ARGOCD_APP_NAME = "{{ARGOCD_APP_NAME}}"
    PLACEHOLDER_GITOPS_REPO_URL = "{{GITOPS_REPO_URL}}"

    def __init__(
        self,
        template_dir: Optional[Path] = None,
        output_base_dir: Optional[Path] = None
    ):
        """
        Initialize the template service

        Args:
            template_dir: Path to template directory (default: template/git-ops)
            output_base_dir: Base path for output (default: temp/git-ops)
        """
        settings = get_settings()

        # Set default paths relative to project root
        project_root = Path(__file__).parent.parent.parent
        self.template_dir = template_dir or project_root / "app" / "templates" / "git-ops"
        self.output_base_dir = output_base_dir or project_root / "tmp" / "git-ops"

        # Ensure output directory exists
        self.output_base_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"GitOpsTemplateService initialized")
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

    def build_replacement_map(
        self,
        microservice_name: str,
        microservice_url: str,
        container_port: int,
        domain_name: str,
        environment: str,
        git_repo_name: str,
        git_branch: str,
        argocd_app_name: str,
        gitops_repo_url: str,
        environment_variables: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, str]:
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
            environment_variables: Optional list of additional env vars

        Returns:
            Dictionary mapping placeholders to values
        """
        replacements = {
            self.PLACEHOLDER_MICROSERVICE_NAME: microservice_name,
            self.PLACEHOLDER_MICROSERVICE_URL: microservice_url,
            self.PLACEHOLDER_CONTAINER_PORT: str(container_port),
            self.PLACEHOLDER_DOMAIN_NAME: domain_name,
            self.PLACEHOLDER_ENVIRONMENT: environment,
            self.PLACEHOLDER_GIT_REPO_NAME: git_repo_name,
            self.PLACEHOLDER_GIT_BRANCH: git_branch,
            self.PLACEHOLDER_ARGOCD_APP_NAME: argocd_app_name,
            self.PLACEHOLDER_GITOPS_REPO_URL: gitops_repo_url,
        }

        # Add custom environment variables as placeholders
        if environment_variables:
            for env_var in environment_variables:
                placeholder = f"{{{{{env_var['name']}}}}}"
                replacements[placeholder] = env_var['value']

        logger.info(f"Built replacement map with {len(replacements)} variables")
        return replacements

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
        argocd_app_name: str,
        gitops_repo_url: str,
        environment_variables: Optional[List[Dict[str, str]]] = None
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
            argocd_app_name: ArgoCD application name
            gitops_repo_url: GitOps repository URL
            environment_variables: Optional list of additional env vars

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

        # Create output directory for this microservice
        output_dir = self.output_base_dir / microservice_name
        if output_dir.exists():
            logger.info(f"Removing existing output directory: {output_dir}")
            shutil.rmtree(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")

        # Build replacement map
        replacements = self.build_replacement_map(
            microservice_name=microservice_name,
            microservice_url=microservice_url,
            container_port=container_port,
            domain_name=domain_name,
            environment=environment,
            git_repo_name=git_repo_name,
            git_branch=git_branch,
            argocd_app_name=argocd_app_name,
            gitops_repo_url=gitops_repo_url,
            environment_variables=environment_variables
        )

        # Get template files
        template_files = self.get_template_files()

        # Process each file
        processed_files = []
        for template_file in template_files:
            try:
                # Calculate relative path to maintain structure
                relative_path = template_file.relative_to(self.template_dir)
                output_file = output_dir / relative_path

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
        }

        return {
            'output_directory': str(output_dir),
            'processed_files': processed_files,
            'total_files_processed': len(processed_files),
            'template_variables': readable_replacements
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
