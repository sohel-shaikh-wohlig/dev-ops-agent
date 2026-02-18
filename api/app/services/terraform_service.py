"""
Terraform Provisioning Service
Renders Terraform templates, pushes to a feature branch in the Terraform repo,
and opens a Pull Request so Atlantis can auto-plan.
"""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from app.core.logging_config import logger
from app.models.terraform import TerraformProvisionRequest
from app.services.git_service import git_service
from app.utils.template_helpers import (
    extract_env_config,
    load_client_config,
    read_template,
    render_template,
)


# Resolve paths relative to the project root (api/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = _PROJECT_ROOT / "app" / "templates" / "terraform"
CLIENT_CONFIG_DIR = _PROJECT_ROOT / "app" / "client_config"
TEMP_DIR = _PROJECT_ROOT / "app" / "temp"


class TerraformService:
    """
    Service for Terraform resource provisioning via GitOps.

    Responsibilities:
      - Load .tf template files from templates/terraform/
      - Load per-client YAML configs from client_config/
      - Replace placeholders and render Terraform content
      - Push rendered file to a feature branch and open a PR
    """

    def __init__(
        self,
        template_dir: Path = TEMPLATE_DIR,
        client_config_dir: Path = CLIENT_CONFIG_DIR,
    ) -> None:
        self.template_dir = template_dir
        self.client_config_dir = client_config_dir

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def provision(self, request: TerraformProvisionRequest) -> Dict[str, Any]:
        """
        Process a Terraform provisioning request via GitOps.

        Renders the template, clones the Terraform repo, creates a feature
        branch, commits the rendered file, pushes, and opens a PR.

        Args:
            request: Validated TerraformProvisionRequest

        Returns:
            Dict with status, resource_type, environment, branch, pr_url.

        Raises:
            FileNotFoundError: template or client config missing
            KeyError: environment section missing in YAML
            ValueError: required resource_config fields missing
            RuntimeError: git or PR creation failure
        """
        logger.info(
            f"Processing Terraform provision | "
            f"client={request.client_name} | "
            f"env={request.environment} | "
            f"resource_type={request.resource_type}"
        )

        # Step 1 — render template
        template_content = read_template(
            self.template_dir, request.resource_type, extension=".tf"
        )

        client_cfg = load_client_config(
            self.client_config_dir, request.client_name
        )
        env_cfg = extract_env_config(
            client_cfg,
            section="gcp",
            environment=request.environment,
            client_name=request.client_name,
        )

        replacements = self._build_replacements(
            request=request,
            env_cfg=env_cfg,
        )

        rendered = render_template(template_content, replacements)

        logger.info(
            f"Terraform template rendered | "
            f"client={request.client_name} | "
            f"resource_type={request.resource_type} | "
            f"placeholders_replaced={len(replacements)}"
        )

        # Step 2 — GitOps: clone, branch, commit, push, PR
        workspace = TEMP_DIR / f"validation_{uuid4().hex[:8]}"
        clone_dir = workspace / "repo"

        try:
            # Clone terraform repo (main branch, shallow)
            success, error = git_service.clone_repository(
                git_url=request.terraform_repo_url,
                target_dir=clone_dir,
                branch="main",
                depth=1,
            )
            if not success:
                raise RuntimeError(f"Failed to clone terraform repo: {error}")

            # Create feature branch
            date_stamp = datetime.now().strftime("%Y%m%d%H%M")
            branch_name = (
                f"tf/{request.client_name}/{request.environment}"
                f"/{request.resource_type}/{date_stamp}"
            )

            success, error = git_service.create_and_checkout_branch(
                clone_dir, branch_name
            )
            if not success:
                raise RuntimeError(f"Failed to create branch: {error}")

            # Write rendered .tf file
            tf_dir = (
                clone_dir / "resources"
                / request.resource_type
                / request.environment
            )
            tf_dir.mkdir(parents=True, exist_ok=True)
            tf_file = tf_dir / f"{request.resource_type}.tf"

            # Merge into existing file if it exists and resource type is gcs
            if tf_file.exists() and request.resource_type == "gcs":
                logger.info(
                    f"File already exists — merging new GCS bucket into: {tf_file}"
                )
                existing_content = tf_file.read_text(encoding="utf-8")
                content_to_write = self._merge_gcs_tf_content(
                    existing_content, rendered
                )
            else:
                content_to_write = rendered

            tf_file.write_text(content_to_write, encoding="utf-8")
            logger.info(f"Wrote rendered Terraform to {tf_file}")
            
            # Stage and commit
            success, error = git_service.add_all(clone_dir)
            if not success:
                raise RuntimeError(f"Failed to stage changes: {error}")

            commit_msg = (
                f"feat: add {request.resource_type} for "
                f"{request.client_name}/{request.environment}"
            )
            success, error, _ = git_service.commit_changes(
                clone_dir, commit_msg
            )
            if not success:
                raise RuntimeError(f"Failed to commit: {error}")

            # Push branch
            success, error = git_service.push_branch(clone_dir, branch_name)
            if not success:
                raise RuntimeError(f"Failed to push branch: {error}")

            # Create Pull Request
            pr_title = (
                f"[Terraform] {request.resource_type} — "
                f"{request.client_name}/{request.environment}"
            )
            pr_body = (
                f"Automated Terraform provisioning\n\n"
                f"- **Client:** {request.client_name}\n"
                f"- **Environment:** {request.environment}\n"
                f"- **Resource:** {request.resource_type}\n"
            )

            success, error, pr_url = git_service.create_pull_request(
                repo_url=request.terraform_repo_url,
                branch=branch_name,
                base="main",
                title=pr_title,
                body=pr_body,
            )
            if not success:
                raise RuntimeError(f"Failed to create PR: {error}")

            logger.info(
                f"Terraform GitOps complete | branch={branch_name} | pr={pr_url}"
            )

            return {
                "status": "success",
                "message": "Terraform PR created successfully",
                "resource_type": request.resource_type,
                "environment": request.environment,
                "branch": branch_name,
                "pr_url": pr_url,
            }

        finally:
            # Always clean up workspace
            if workspace.exists():
                logger.info(f"Cleaning up workspace: {workspace}")
                shutil.rmtree(workspace, ignore_errors=True)

    # ------------------------------------------------------------------
    # Private — terraform-specific logic
    # ------------------------------------------------------------------

    def _build_replacements(
        self,
        request: TerraformProvisionRequest,
        env_cfg: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Build the placeholder -> value mapping.

        Merges data from:
          - request fields (client_name, environment)
          - env_cfg (project_id, project_location)
          - resource_config (bucket_name, etc.)
        """
        # Resolve project_location (some configs use 'location' as key)
        project_location = env_cfg.get(
            "project_location", env_cfg.get("location")
        )
        project_id = env_cfg.get("project_id")

        if not project_id:
            raise KeyError(
                f"'project_id' missing from client config for "
                f"environment '{request.environment}'"
            )
        if not project_location:
            raise KeyError(
                f"'project_location' (or 'location') missing from client "
                f"config for environment '{request.environment}'"
            )

        # Validate resource_config based on resource_type
        self._validate_resource_config(
            request.resource_type, request.resource_config
        )

        replacements: Dict[str, str] = {
            "{{client}}": request.client_name,
            "{{environment}}": request.environment,
            "{{project_id}}": str(project_id),
            "{{project_location}}": str(project_location),
        }

        # Add every key from resource_config as a placeholder
        for key, value in request.resource_config.items():
            replacements[f"{{{{{key}}}}}"] = str(value)

        return replacements

    @staticmethod
    def _validate_resource_config(
        resource_type: str, resource_config: Dict[str, Any]
    ) -> None:
        """Validate that required resource_config keys are present."""
        required_keys: Dict[str, list] = {
            "gcs": ["bucket_name"],
        }

        keys_needed = required_keys.get(resource_type, [])
        missing = [k for k in keys_needed if k not in resource_config]
        if missing:
            raise ValueError(
                f"resource_config for '{resource_type}' is missing "
                f"required keys: {missing}"
            )

    @staticmethod
    def _merge_gcs_tf_content(existing_content: str, rendered: str) -> str:
        """
        Append a new GCS bucket object from rendered into the gcs_bucket
        array already present in existing_content.

        Uses balanced bracket/brace counting to find the correct closing
        positions, avoiding false matches on nested structures such as
        names = ["..."] or labels = { ... }.

        Args:
            existing_content: Current contents of the .tf file on disk.
            rendered: Freshly rendered template containing the new bucket object.

        Returns:
            Merged HCL string with the new bucket appended to gcs_bucket array.

        Raises:
            ValueError: If the expected HCL structure is not found in either string.
        """

        def find_matching_close(
            text: str, open_pos: int, open_char: str, close_char: str
        ) -> int:
            """
            Return the index of the closing character that balances the one
            at open_pos, using depth counting to skip nested pairs.
            Returns -1 if no match is found.
            """
            depth = 0
            for i in range(open_pos, len(text)):
                if text[i] == open_char:
                    depth += 1
                elif text[i] == close_char:
                    depth -= 1
                    if depth == 0:
                        return i
            return -1

        # --- Extract new bucket object from rendered template ---
        # Locate "gcs_bucket = [" then find the { ... } object inside it.
        gcs_match = re.search(r'gcs_bucket\s*=\s*\[', rendered)
        if not gcs_match:
            raise ValueError(
                "Could not find 'gcs_bucket = [' in rendered template."
            )
        bracket_open = rendered.index('[', gcs_match.start())
        obj_open = rendered.index('{', bracket_open)
        obj_close = find_matching_close(rendered, obj_open, '{', '}')
        if obj_close == -1:
            raise ValueError(
                "Could not find closing '}' for bucket object in rendered template."
            )
        new_bucket_object = rendered[obj_open:obj_close + 1].strip()

        # --- Locate the gcs_bucket array in the existing file ---
        gcs_match_ex = re.search(r'gcs_bucket\s*=\s*\[', existing_content)
        if not gcs_match_ex:
            raise ValueError(
                "Could not locate 'gcs_bucket = [' in existing tf file. "
                "Cannot merge new bucket configuration."
            )
        bracket_open_ex = existing_content.index('[', gcs_match_ex.start())
        bracket_close_ex = find_matching_close(
            existing_content, bracket_open_ex, '[', ']'
        )
        if bracket_close_ex == -1:
            raise ValueError(
                "Could not find closing ']' for gcs_bucket array in existing tf file."
            )

        # Insert the new object immediately before the closing ], separated
        # by a comma so the resulting HCL array remains valid.
        merged = (
            existing_content[:bracket_close_ex]
            + f",\n    {new_bucket_object}\n  "
            + existing_content[bracket_close_ex:]
        )
        return merged
