"""
GitOps Template Processing Service
Handles template file processing with variable substitution
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
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

    # CronJobs placeholders (supports multiple cronjobs)
    PLACEHOLDER_CRONJOBS_YAML = "{{CRONJOBS_YAML}}"
    PLACEHOLDER_CRONJOBS_COUNT = "{{CRONJOBS_COUNT}}"

    # Worker placeholders (optional worker deployment)
    PLACEHOLDER_WORKER_YAML = "{{WORKER_YAML}}"
    PLACEHOLDER_WORKER_COUNT = "{{WORKER_COUNT}}"

    # UAT-specific Istio placeholders (gateway and virtualservice)
    PLACEHOLDER_GATEWAY_YAML = "{{GATEWAY_YAML}}"
    PLACEHOLDER_VIRTUALSERVICE_YAML = "{{VIRTUALSERVICE_YAML}}"

    # Environment constants
    ENV_UAT = "uat"
    ENV_DEV = "dev"

    # Workflow file names (environment-specific)
    WORKFLOW_FILE_DEV = "workflows.yaml"
    WORKFLOW_FILE_UAT = "workflows-uat.yaml"
    # Pattern for environment-specific workflow templates: workflows-{env}.yaml
    # e.g. workflows-test.yaml, workflows-dev.yaml, workflows-prod.yaml
    WORKFLOW_FILE_ENV_TEMPLATE = "workflows-{env}.yaml"

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

    def format_cronjobs_yaml(self, cronjobs: List[Dict[str, Any]], indent: int = 0) -> str:
        """
        Format multiple cronjob configurations as YAML for values.yaml with indexed keys.

        Generates a flat structure under 'cronjob:' (singular) with numbered keys:
            cronjob:
              name1: "cronjob-data-sync"
              suspend1: false
              schedule1: "0 2 * * *"
              cmd1: ["npm", "run", "sync"]
              name2: "cronjob-update-portfolio"
              suspend2: true
              schedule2: "0 3 * * *"
              cmd2: ["npm", "run", "update"]

        This structure allows Helm templates to reference values like:
            {{ .Values.cronjob.name1 }}, {{ .Values.cronjob.name2 }}, etc.

        Args:
            cronjobs: List of dictionaries containing cronjob configurations
                Each dict expected keys: name, schedule, suspend, cmd
            indent: Number of spaces for base indentation

        Returns:
            YAML formatted cronjob section string with numbered keys.
            Returns empty string if cronjobs list is empty or None.
        """
        if not cronjobs or len(cronjobs) == 0:
            return ""

        indent_str = " " * indent
        lines = [f"{indent_str}cronjob:"]

        for idx, cronjob in enumerate(cronjobs):
            # Use 1-based index for keys (name1, name2, etc.)
            key_idx = idx + 1

            # Format name with index
            name = cronjob.get('name', f'job-{key_idx}')
            lines.append(f"{indent_str}  name{key_idx}: \"cronjob-{name}\"")

            # Format suspend with index (boolean)
            suspend = cronjob.get('suspend', False)
            suspend_str = str(suspend).lower() if isinstance(suspend, bool) else str(suspend)
            lines.append(f"{indent_str}  suspend{key_idx}: {suspend_str}")

            # Format schedule with index
            schedule = cronjob.get('schedule', '0 * * * *')
            lines.append(f"{indent_str}  schedule{key_idx}: \"{schedule}\"")

            # Format cmd with index (list of strings)
            cmd = cronjob.get('cmd', [])
            if isinstance(cmd, list) and cmd:
                cmd_formatted = ', '.join(f'"{c}"' for c in cmd)
                lines.append(f"{indent_str}  cmd{key_idx}: [{cmd_formatted}]")
            elif isinstance(cmd, str):
                lines.append(f"{indent_str}  cmd{key_idx}: [\"{cmd}\"]")
            else:
                lines.append(f"{indent_str}  cmd{key_idx}: []")

        return '\n'.join(lines)

    def format_cronjob_cmd(self, cmd: Any) -> str:
        """
        Format cronjob command as YAML array string

        Args:
            cmd: Command as string or list of strings

        Returns:
            YAML array formatted string
        """
        if not cmd:
            return "[]"

        if isinstance(cmd, list):
            return '[' + ', '.join(f'"{c}"' for c in cmd) + ']'
        elif isinstance(cmd, str):
            return f'["{cmd}"]'
        return "[]"

    def generate_cronjob_manifests(
        self,
        cronjobs: List[Dict[str, Any]],
        template_content: str,
        output_dir: Path,
        base_replacements: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Generate individual cronjob manifest files for each cronjob in the list.

        For each cronjob, creates a unique manifest file named 'cronjob-{name}.yaml'
        with numbered keys (name1, suspend1, schedule1, cmd1 for first item, etc.).

        The template uses index 1 placeholders (.Values.cronjob.name1, etc.).
        This method transforms these to the appropriate index for each cronjob:
        - First cronjob: keeps name1, suspend1, schedule1, cmd1
        - Second cronjob: transforms to name2, suspend2, schedule2, cmd2
        - And so on...

        Args:
            cronjobs: List of cronjob configurations
            template_content: Content of the cronjob.yaml template
            output_dir: Directory to write the generated manifest files
            base_replacements: Base replacement map for common placeholders

        Returns:
            List of dictionaries with info about each generated file
        """
        if not cronjobs or len(cronjobs) == 0:
            return []

        generated_files = []

        for idx, cronjob in enumerate(cronjobs):
            # Use 1-based index for keys (name1, name2, etc.)
            key_idx = idx + 1

            cronjob_name = cronjob.get('name', f'job-{key_idx}')
            output_filename = f"cronjob-{cronjob_name}.yaml"
            output_file = output_dir / output_filename

            logger.info(f"Generating cronjob manifest: {output_filename} (index: {key_idx})")

            # Start with the template content
            cronjob_content = template_content

            # Transform the index in Helm template placeholders
            # Template has: .Values.cronjob.name1, .Values.cronjob.suspend1, etc.
            # For each cronjob, we replace index '1' with the appropriate key_idx
            # This preserves the Helm template syntax but updates the index
            index_replacements = {
                '.Values.cronjob.name1': f'.Values.cronjob.name{key_idx}',
                '.Values.cronjob.suspend1': f'.Values.cronjob.suspend{key_idx}',
                '.Values.cronjob.schedule1': f'.Values.cronjob.schedule{key_idx}',
                '.Values.cronjob.cmd1': f'.Values.cronjob.cmd{key_idx}',
            }

            replacement_count = 0
            for old_ref, new_ref in index_replacements.items():
                count = cronjob_content.count(old_ref)
                if count > 0:
                    cronjob_content = cronjob_content.replace(old_ref, new_ref)
                    replacement_count += count
                    logger.debug(f"Replaced {count} occurrences of {old_ref} with {new_ref}")

            # Apply base replacements for other placeholders (namespace, image, etc.)
            # These are {{PLACEHOLDER}} style, not Helm style
            for placeholder, value in base_replacements.items():
                if placeholder in cronjob_content:
                    cronjob_content = cronjob_content.replace(placeholder, value)

            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)

            # Write the generated manifest
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cronjob_content)

            generated_files.append({
                'source_path': 'template/git-ops/templates/cronjob.yaml',
                'output_path': str(output_file),
                'cronjob_name': cronjob_name,
                'cronjob_index': key_idx,
                'replacements_made': replacement_count
            })

            logger.info(f"Generated cronjob manifest: {output_file}")

        logger.info(f"Generated {len(generated_files)} individual cronjob manifest files")
        return generated_files

    def format_worker_yaml(self, worker: Dict[str, Any], indent: int = 0) -> str:
        """
        Format worker configuration as YAML for values.yaml.

        Generates values for worker deployment:
            WORKER_LANGUAGE_TRANSLATION_NAME: "worker-language-translation"
            worker:
              enabled: true

        Note:
        - WORKER_LANGUAGE_TRANSLATION (workerType) is added to config section via env_vars
        - Secret names are dynamic based on microservice name:
          - Vertex AI: {microservice_name}-ai
          - BigQuery: {microservice_name}-bq-creds

        Args:
            worker: Dictionary containing worker configuration
                Expected keys: name, worker_type, secrets, additional_env
            indent: Number of spaces for base indentation

        Returns:
            YAML formatted worker section string.
            Returns empty string if worker is None or empty.
        """
        if not worker:
            return ""

        indent_str = " " * indent
        lines = []

        # Get worker configuration
        name = worker.get('name', 'language-translation')
        worker_full_name = f"worker-{name}"

        # Add WORKER_LANGUAGE_TRANSLATION_NAME at root level (used by template for deployment name)
        lines.append(f"{indent_str}WORKER_LANGUAGE_TRANSLATION_NAME: \"{worker_full_name}\"")

        # Add worker section (secrets are now dynamic based on microservice name)
        lines.append(f"{indent_str}worker:")
        lines.append(f"{indent_str}  enabled: true")

        return '\n'.join(lines)

    def generate_worker_manifest(
        self,
        worker: Dict[str, Any],
        template_content: str,
        output_dir: Path,
        base_replacements: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Generate worker manifest file from the worker configuration.

        Creates a manifest file named 'worker-{name}.yaml' with conditional
        secret volumes and env vars based on the 'secrets' field:
        - If 'vertex_ai' in secrets: includes vertex-ai-credentials-volume and GOOGLE_APPLICATION_CREDENTIALS env
        - If 'bq' in secrets: includes bq-credentials-volume and BQ_* env vars
        - If neither: removes these volumes and env vars to avoid deployment errors

        Args:
            worker: Worker configuration dictionary
            template_content: Content of the worker.yaml template
            output_dir: Directory to write the generated manifest file
            base_replacements: Base replacement map for common placeholders

        Returns:
            List with a single dictionary containing info about the generated file
        """
        if not worker:
            return []

        generated_files = []

        worker_name = worker.get('name', 'language-translation')
        output_filename = f"worker-{worker_name}.yaml"
        output_file = output_dir / output_filename

        logger.info(f"Generating worker manifest: {output_filename}")

        # Get enabled secrets (normalize to lowercase for comparison)
        secrets = worker.get('secrets', []) or []
        secrets_lower = [s.lower() for s in secrets]
        enable_vertex_ai = 'vertex_ai' in secrets_lower or 'vertexai' in secrets_lower
        enable_bq = 'bq' in secrets_lower or 'bigquery' in secrets_lower

        logger.info(f"Worker secrets configuration - Vertex AI: {enable_vertex_ai}, BigQuery: {enable_bq}")

        # Build the worker manifest dynamically based on enabled secrets
        worker_content = self._build_worker_manifest(
            worker=worker,
            enable_vertex_ai=enable_vertex_ai,
            enable_bq=enable_bq
        )

        # Apply base replacements for other placeholders (namespace, image, etc.)
        replacement_count = 0
        for placeholder, value in base_replacements.items():
            count = worker_content.count(placeholder)
            if count > 0:
                worker_content = worker_content.replace(placeholder, value)
                replacement_count += count

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write the generated manifest
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(worker_content)

        generated_files.append({
            'source_path': 'template/git-ops/templates/worker.yaml',
            'output_path': str(output_file),
            'worker_name': worker_name,
            'secrets_enabled': secrets,
            'replacements_made': replacement_count
        })

        logger.info(f"Generated worker manifest: {output_file}")
        logger.info(f"Generated {len(generated_files)} worker manifest file")
        return generated_files

    def _build_worker_manifest(
        self,
        worker: Dict[str, Any],
        enable_vertex_ai: bool,
        enable_bq: bool
    ) -> str:
        """
        Build worker manifest YAML with conditional secrets.

        Args:
            worker: Worker configuration dictionary
            enable_vertex_ai: Whether to include Vertex AI credential volumes/env
            enable_bq: Whether to include BigQuery credential volumes/env

        Returns:
            Complete worker manifest YAML string
        """
        # Build env section (no hardcoded suffixes - dynamic based on secrets)
        env_lines = [
            "          env:",
            "            - name: NODE_ENV",
            "              value: {{ .Values.config.NODE_ENV | quote }}",
            "            - name: WORKER_TYPE",
            "              value: {{ .Values.config.WORKER_LANGUAGE_TRANSLATION | quote }}",
        ]

        # Add Vertex AI credential env var only if enabled
        if enable_vertex_ai:
            env_lines.append("            - name: GOOGLE_APPLICATION_CREDENTIALS")
            env_lines.append("              value: /etc/ai-credentials/credentials.json")

        # Add BigQuery credential env vars only if enabled
        if enable_bq:
            env_lines.append("            - name: BQ_DATASET_KEY")
            env_lines.append("              value: /etc/credentials/bq_credentials.json")
            env_lines.append("            - name: BQ_PORTFOLIO_DATASET_KEY")
            env_lines.append("              value: /etc/credentials/bq_avs_credentials.json")

        # Build volumeMounts section
        volume_mounts_lines = [
            "          volumeMounts:",
            "            - name: db-certs",
            "              mountPath: /app/certs",
            "              readOnly: true",
        ]

        if enable_vertex_ai:
            volume_mounts_lines.extend([
                "            - name: vertex-ai-credentials-volume",
                "              mountPath: /etc/ai-credentials",
                "              readOnly: true",
            ])

        if enable_bq:
            volume_mounts_lines.extend([
                "            - name: bq-credentials-volume",
                "              mountPath: /etc/credentials",
                "              readOnly: true",
            ])

        # Build volumes section
        volumes_lines = [
            "      volumes:",
        ]

        if enable_vertex_ai:
            volumes_lines.extend([
                "        - name: vertex-ai-credentials-volume",
                "          secret:",
                "            secretName: {{MICRO_SERVICE_NAME}}-ai",
                "            items:",
                "              - key: credentials.json",
                "                path: credentials.json",
            ])

        if enable_bq:
            volumes_lines.extend([
                "        - name: bq-credentials-volume",
                "          secret:",
                "            secretName: {{MICRO_SERVICE_NAME}}-bq-creds",
                "            items:",
                "              - key: bq_credentials.json",
                "                path: bq_credentials.json",
                "              - key: bq_avs_credentials.json",
                "                path: bq_avs_credentials.json",
            ])

        # Always include db-certs volume
        volumes_lines.extend([
            "        - name: db-certs",
            "          secret:",
            "            secretName: db-certs",
            "            defaultMode: 400",
        ])

        # Assemble the full manifest
        manifest = f"""kind: Deployment
apiVersion: apps/v1
metadata:
  name: {{{{ .Values.WORKER_LANGUAGE_TRANSLATION_NAME | quote }}}}
  annotations:
    repoUrl: {{{{ .Values.annotations.repoUrl | quote }}}}
  labels:
    application: {{{{ .Values.labels.application }}}}
    env: {{{{ .Values.labels.env }}}}
spec:
  replicas: {{{{ .Values.replicasCount }}}}
  selector:
    matchLabels:
      app: {{{{ .Values.WORKER_LANGUAGE_TRANSLATION_NAME | quote }}}}
  template:
    metadata:
      labels:
        app: {{{{ .Values.WORKER_LANGUAGE_TRANSLATION_NAME | quote }}}}
      annotations:
        linkerd.io/inject: disabled
    spec:
      containers:
        - name: {{{{ .Values.WORKER_LANGUAGE_TRANSLATION_NAME | quote }}}}
          image: {{{{ .Values.image.name }}}}:{{{{ .Values.image.tag }}}}
          ports:
            - containerPort: {{{{ .Values.containerPort }}}}
              protocol: TCP
          imagePullPolicy: {{{{ .Values.image.pullPolicy }}}}
{chr(10).join(env_lines)}
          envFrom:
            - configMapRef:
                name: {{{{ .Values.name }}}}
          resources:
            {{{{- toYaml .Values.resources | nindent 12 }}}}
{chr(10).join(volume_mounts_lines)}
{chr(10).join(volumes_lines)}
"""
        return manifest

    def generate_gateway_manifest(
        self,
        microservice_name: str,
        domain_name: str,
        output_dir: Path,
        base_replacements: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Generate Istio Gateway manifest for UAT environment.

        Creates a gateway.yaml file that configures Istio ingress gateway
        for the microservice.

        Args:
            microservice_name: Name of the microservice
            domain_name: Domain name for the gateway host
            output_dir: Directory to write the generated manifest file
            base_replacements: Base replacement map for common placeholders

        Returns:
            List with a single dictionary containing info about the generated file
        """
        generated_files = []

        output_filename = "gateway.yaml"
        output_file = output_dir / output_filename

        logger.info(f"Generating Istio Gateway manifest: {output_filename}")

        # Build the Gateway manifest
        gateway_content = self._build_gateway_manifest(microservice_name, domain_name)

        # Apply base replacements for other placeholders
        replacement_count = 0
        for placeholder, value in base_replacements.items():
            count = gateway_content.count(placeholder)
            if count > 0:
                gateway_content = gateway_content.replace(placeholder, value)
                replacement_count += count

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write the generated manifest
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(gateway_content)

        generated_files.append({
            'source_path': 'generated/gateway.yaml',
            'output_path': str(output_file),
            'manifest_type': 'gateway',
            'replacements_made': replacement_count
        })

        logger.info(f"Generated Istio Gateway manifest: {output_file}")
        return generated_files

    def _build_gateway_manifest(
        self,
        microservice_name: str,
        domain_name: str
    ) -> str:
        """
        Build Istio Gateway manifest YAML.

        Args:
            microservice_name: Name of the microservice
            domain_name: Domain name for the gateway host

        Returns:
            Complete Gateway manifest YAML string
        """
        manifest = f"""apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: {{{{ .Values.name }}}}-gateway
  labels:
    application: {{{{ .Values.labels.application }}}}
    env: {{{{ .Values.labels.env }}}}
spec:
  selector:
    istio: ingressgateway
  servers:
    - port:
        number: 80
        name: http
        protocol: HTTP
      hosts:
        - {{{{ .Values.domainName | quote }}}}
    - port:
        number: 443
        name: https
        protocol: HTTPS
      tls:
        mode: SIMPLE
        credentialName: {{{{ .Values.name }}}}-tls
      hosts:
        - {{{{ .Values.domainName | quote }}}}
"""
        return manifest

    def generate_virtualservice_manifest(
        self,
        microservice_name: str,
        domain_name: str,
        container_port: int,
        output_dir: Path,
        base_replacements: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Generate Istio VirtualService manifest for UAT environment.

        Creates a virtualservice.yaml file that configures routing rules
        for the microservice.

        Args:
            microservice_name: Name of the microservice
            domain_name: Domain name for the virtual service host
            container_port: Container port for routing
            output_dir: Directory to write the generated manifest file
            base_replacements: Base replacement map for common placeholders

        Returns:
            List with a single dictionary containing info about the generated file
        """
        generated_files = []

        output_filename = "virtualservice.yaml"
        output_file = output_dir / output_filename

        logger.info(f"Generating Istio VirtualService manifest: {output_filename}")

        # Build the VirtualService manifest
        virtualservice_content = self._build_virtualservice_manifest(
            microservice_name, domain_name, container_port
        )

        # Apply base replacements for other placeholders
        replacement_count = 0
        for placeholder, value in base_replacements.items():
            count = virtualservice_content.count(placeholder)
            if count > 0:
                virtualservice_content = virtualservice_content.replace(placeholder, value)
                replacement_count += count

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write the generated manifest
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(virtualservice_content)

        generated_files.append({
            'source_path': 'generated/virtualservice.yaml',
            'output_path': str(output_file),
            'manifest_type': 'virtualservice',
            'replacements_made': replacement_count
        })

        logger.info(f"Generated Istio VirtualService manifest: {output_file}")
        return generated_files

    def _build_virtualservice_manifest(
        self,
        microservice_name: str,
        domain_name: str,
        container_port: int
    ) -> str:
        """
        Build Istio VirtualService manifest YAML.

        Args:
            microservice_name: Name of the microservice
            domain_name: Domain name for the virtual service host
            container_port: Container port for routing

        Returns:
            Complete VirtualService manifest YAML string
        """
        manifest = f"""apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: {{{{ .Values.name }}}}-vs
  labels:
    application: {{{{ .Values.labels.application }}}}
    env: {{{{ .Values.labels.env }}}}
spec:
  hosts:
    - {{{{ .Values.domainName | quote }}}}
  gateways:
    - {{{{ .Values.name }}}}-gateway
  http:
    - match:
        - uri:
            prefix: /
      route:
        - destination:
            host: {{{{ .Values.name }}}}
            port:
              number: {{{{ .Values.containerPort }}}}
      corsPolicy:
        allowOrigins:
          - regex: ".*"
        allowMethods:
          - GET
          - POST
          - PUT
          - DELETE
          - PATCH
          - OPTIONS
        allowHeaders:
          - "*"
        allowCredentials: true
        maxAge: "24h"
"""
        return manifest

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
        env_content: Optional[str] = None,
        cronjobs: Optional[List[Dict[str, Any]]] = None,
        worker: Optional[Dict[str, Any]] = None
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
            cronjobs: Optional list of cronjob configurations, each with keys: name, schedule, suspend, cmd
            worker: Optional worker configuration with keys: name, worker_type, vertex_ai_secret, bigquery_secret, additional_env

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

        # Add cronjobs configuration placeholders if provided
        if cronjobs and len(cronjobs) > 0:
            logger.info("=== Processing CronJobs Configuration ===")
            logger.info(f"Number of cronjobs: {len(cronjobs)}")
            for idx, cj in enumerate(cronjobs):
                logger.info(f"CronJob [{idx + 1}] name: {cj.get('name', '')}")
                logger.info(f"CronJob [{idx + 1}] schedule: {cj.get('schedule', '0 * * * *')}")
                logger.info(f"CronJob [{idx + 1}] suspend: {cj.get('suspend', False)}")
                logger.info(f"CronJob [{idx + 1}] command: {cj.get('cmd', [])}")

            # Full cronjobs YAML section for values.yaml with indexed keys
            replacements[self.PLACEHOLDER_CRONJOBS_YAML] = self.format_cronjobs_yaml(cronjobs)
            # Set CRONJOBS_COUNT to the total number of cronjobs
            replacements[self.PLACEHOLDER_CRONJOBS_COUNT] = str(len(cronjobs))
            logger.info(f"CRONJOBS_COUNT set to: {len(cronjobs)}")
            logger.info("CronJobs placeholders added to replacement map")
        else:
            logger.info("=== CronJobs Configuration: Not Provided ===")
            logger.info("Skipping cronjobs setup - no cronjobs data in request")
            # If no cronjobs provided, set empty placeholders
            replacements[self.PLACEHOLDER_CRONJOBS_YAML] = ""
            replacements[self.PLACEHOLDER_CRONJOBS_COUNT] = "0"
            logger.info("CronJobs placeholder set to empty string, CRONJOBS_COUNT set to 0")

        # Add worker configuration placeholders if provided
        if worker:
            logger.info("=== Processing Worker Configuration ===")
            worker_name = worker.get('name', 'language-translation')
            worker_type = worker.get('worker_type', worker.get('workerType', 'languageTranslation'))
            secrets = worker.get('secrets', []) or []
            vertex_ai_secret = worker.get('vertex_ai_secret', worker.get('vertexAiSecret', ''))
            bigquery_secret = worker.get('bigquery_secret', worker.get('bigquerySecret', ''))
            additional_env = worker.get('additional_env', worker.get('additionalEnv', {}))

            logger.info(f"Worker name: {worker_name}")
            logger.info(f"Worker type: {worker_type}")
            logger.info(f"Enabled secrets: {secrets}")
            logger.info(f"Vertex AI secret: {vertex_ai_secret}")
            logger.info(f"BigQuery secret: {bigquery_secret}")
            logger.info(f"Additional env: {additional_env}")

            # Add WORKER_LANGUAGE_TRANSLATION to env_vars for config.data section
            # This maps worker.workerType -> config.data.WORKER_LANGUAGE_TRANSLATION
            env_vars['WORKER_LANGUAGE_TRANSLATION'] = worker_type
            logger.info(f"Added WORKER_LANGUAGE_TRANSLATION={worker_type} to config.data section")

            # Add additional_env variables to env_vars for config section in values.yaml ONLY
            # These will be added to the config: section in values.yaml but NOT to configmap.yaml
            # The configmap already references values.yaml via {{ .Values.config.KEY | quote }}
            if additional_env:
                for key, value in additional_env.items():
                    env_vars[key] = value
                    logger.info(f"Added {key}={value} to values.yaml config section only")

            # Re-generate ONLY the values.yaml placeholder with the additional worker config values
            # DO NOT regenerate configmap placeholder - additional_env should only be in values.yaml
            replacements[self.PLACEHOLDER_ENVIRONMENT_VARIABLES_YAML] = self.format_env_vars_values_yaml(env_vars)

            # Full worker YAML section for values.yaml
            replacements[self.PLACEHOLDER_WORKER_YAML] = self.format_worker_yaml(worker)
            # Set WORKER_COUNT to 1 (single worker per request)
            replacements[self.PLACEHOLDER_WORKER_COUNT] = "1"
            logger.info("Worker placeholders added to replacement map")
        else:
            logger.info("=== Worker Configuration: Not Provided ===")
            logger.info("Skipping worker setup - no worker data in request")
            # If no worker provided, set empty placeholders
            replacements[self.PLACEHOLDER_WORKER_YAML] = ""
            replacements[self.PLACEHOLDER_WORKER_COUNT] = "0"
            logger.info("Worker placeholder set to empty string, WORKER_COUNT set to 0")

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
        env_content: Optional[str] = None,
        cronjobs: Optional[List[Dict[str, Any]]] = None,
        worker: Optional[Dict[str, Any]] = None
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
            cronjobs: Optional list of cronjob configurations, each with keys: name, schedule, suspend, cmd.
                      If None or empty, cronjob template files will be skipped.
            worker: Optional worker configuration with keys: name, worker_type, vertex_ai_secret, bigquery_secret, additional_env.
                    If None, worker template files will be skipped.

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
            env_content=env_content,
            cronjobs=cronjobs,
            worker=worker
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

                # Skip cronjob.yaml from regular processing - we generate individual files separately
                if template_file.name == 'cronjob.yaml':
                    if not cronjobs or len(cronjobs) == 0:
                        logger.info(f"Skipping {relative_path} - no cronjobs configuration provided")
                    else:
                        logger.info(f"Skipping {relative_path} - will generate individual cronjob manifests")
                    continue

                # Skip worker.yaml from regular processing - we generate individual files separately
                if template_file.name == 'worker.yaml':
                    if not worker:
                        logger.info(f"Skipping {relative_path} - no worker configuration provided")
                    else:
                        logger.info(f"Skipping {relative_path} - will generate individual worker manifest")
                    continue

                # Skip vertex-ai-secret.yaml if worker not provided or 'vertex_ai' not in secrets
                if template_file.name == 'vertex-ai-secret.yaml':
                    if not worker:
                        logger.info(f"Skipping {relative_path} - no worker configuration provided")
                        continue
                    worker_secrets = worker.get('secrets', []) or []
                    secrets_lower = [s.lower() for s in worker_secrets]
                    if 'vertex_ai' not in secrets_lower and 'vertexai' not in secrets_lower:
                        logger.info(f"Skipping {relative_path} - 'vertex_ai' not in worker secrets")
                        continue

                # Skip bigquery-secret.yaml if worker not provided or 'bq' not in secrets
                if template_file.name == 'bigquery-secret.yaml':
                    if not worker:
                        logger.info(f"Skipping {relative_path} - no worker configuration provided")
                        continue
                    worker_secrets = worker.get('secrets', []) or []
                    secrets_lower = [s.lower() for s in worker_secrets]
                    if 'bq' not in secrets_lower and 'bigquery' not in secrets_lower:
                        logger.info(f"Skipping {relative_path} - 'bq' not in worker secrets")
                        continue

                # Environment-specific httpproxy.yaml handling
                # UAT: Skip httpproxy.yaml (uses Istio Gateway/VirtualService instead)
                # DEV: Include httpproxy.yaml normally
                if template_file.name == 'httpproxy.yaml':
                    if environment.lower() == self.ENV_UAT:
                        logger.info(f"Skipping {relative_path} - httpproxy.yaml is not used in UAT environment")
                        continue

                # Environment-specific virtual-service.yaml handling
                # UAT: Copy as-is without templating
                # DEV / other envs: Skip for now (will be enabled later based on env & project config)
                if template_file.name == 'virtual-service.yaml':
                    if environment.lower() == self.ENV_UAT:
                        # For UAT: Copy the file directly without template processing
                        logger.info(f"Copying {relative_path} as-is for UAT environment (no templating)")
                        path_parts = relative_path.parts
                        if len(path_parts) >= 1:
                            template_folder = path_parts[0]
                            rest_of_path = Path(*path_parts[1:]) if len(path_parts) > 1 else Path("")
                            output_file = self.output_base_dir / template_folder / microservice_name / rest_of_path
                        else:
                            output_file = self.output_base_dir / microservice_name / relative_path

                        output_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(template_file, output_file)

                        processed_files.append({
                            'source_path': str(template_file),
                            'output_path': str(output_file),
                            'replacements_made': 0,
                            'copy_mode': 'direct'
                        })
                        logger.info(f"Copied: {relative_path} (direct copy, no templating)")
                        continue
                    else:
                        # Skip for all non-UAT environments for now
                        logger.info(f"Skipping {relative_path} - virtual-service.yaml is skipped for '{environment}' environment (will be enabled later based on env & project config)")
                        continue

                # Environment-specific gateway.yaml handling
                # UAT: Process gateway.yaml normally (will be generated later)
                # DEV: Skip gateway.yaml (not used in dev environment)
                if template_file.name == 'gateway.yaml':
                    if environment.lower() == self.ENV_DEV:
                        logger.info(f"Skipping {relative_path} - gateway.yaml is not used in DEV environment")
                        continue
                    elif environment.lower() == self.ENV_UAT:
                        logger.info(f"Skipping {relative_path} - will generate gateway manifest for UAT")
                        continue
                    else:
                        # For other environments, skip by default
                        logger.info(f"Skipping {relative_path} - gateway.yaml is only for UAT environment")
                        continue

                # Note: virtualservice.yaml (without hyphen) handling
                # This is for dynamically generated files, virtual-service.yaml (with hyphen) is handled above
                if template_file.name == 'virtualservice.yaml':
                    if environment.lower() == self.ENV_DEV:
                        logger.info(f"Skipping {relative_path} - virtualservice.yaml is not used in DEV environment")
                        continue
                    elif environment.lower() == self.ENV_UAT:
                        logger.info(f"Skipping {relative_path} - will generate virtualservice manifest for UAT")
                        continue
                    else:
                        # For other environments, skip by default
                        logger.info(f"Skipping {relative_path} - virtualservice.yaml is only for UAT environment")
                        continue

                # Environment-specific workflow file selection
                # Priority:
                #   1. workflows-{env}.yaml (e.g. workflows-test.yaml) — most specific
                #   2. workflows-uat.yaml — legacy UAT-specific (only for UAT env)
                #   3. workflows.yaml — generic fallback (only for non-UAT env)
                env_workflow_file = self.WORKFLOW_FILE_ENV_TEMPLATE.format(env=environment.lower())

                if template_file.name == self.WORKFLOW_FILE_DEV:
                    # Skip generic workflows.yaml if an env-specific file exists or if UAT
                    env_specific_path = template_file.parent / env_workflow_file
                    if env_specific_path.exists():
                        logger.info(f"Skipping {relative_path} - using {env_workflow_file} for {environment} environment")
                        continue
                    if environment.lower() == self.ENV_UAT:
                        logger.info(f"Skipping {relative_path} - using {self.WORKFLOW_FILE_UAT} for UAT environment")
                        continue

                if template_file.name == self.WORKFLOW_FILE_UAT:
                    if environment.lower() != self.ENV_UAT:
                        logger.info(f"Skipping {relative_path} - {self.WORKFLOW_FILE_UAT} is only for UAT environment")
                        continue
                    else:
                        # For UAT, rename the output file to workflows.yaml (standard name)
                        logger.info(f"Using {self.WORKFLOW_FILE_UAT} for UAT environment (will be output as {self.WORKFLOW_FILE_DEV})")

                # Skip env-specific workflow templates that don't match the current environment
                # e.g. skip workflows-test.yaml when deploying to dev
                if template_file.name.startswith("workflows-") and template_file.name.endswith(".yaml") \
                        and template_file.name != self.WORKFLOW_FILE_UAT \
                        and template_file.name != env_workflow_file:
                    logger.info(f"Skipping {relative_path} - workflow template for a different environment")
                    continue

                # Rename env-specific workflow file (e.g. workflows-test.yaml) to workflows.yaml in output
                if template_file.name == env_workflow_file:
                    logger.info(f"Using {env_workflow_file} for {environment} environment")

                # Insert microservice_name after the template folder (git-ops or github)
                # Structure: output_base_dir/git-ops/microservice_name/values.yaml
                path_parts = relative_path.parts
                if len(path_parts) >= 1:
                    template_folder = path_parts[0]  # git-ops or github
                    rest_of_path = Path(*path_parts[1:]) if len(path_parts) > 1 else Path("")

                    # For UAT environment: rename workflows-uat.yaml to workflows.yaml in output
                    if template_file.name == self.WORKFLOW_FILE_UAT and environment.lower() == self.ENV_UAT:
                        # Replace workflows-uat.yaml with workflows.yaml in the output path
                        rest_of_path = Path(str(rest_of_path).replace(self.WORKFLOW_FILE_UAT, self.WORKFLOW_FILE_DEV))
                        logger.info(f"Renaming output file: {self.WORKFLOW_FILE_UAT} -> {self.WORKFLOW_FILE_DEV}")

                    # For env-specific workflows (e.g. workflows-test.yaml): rename to workflows.yaml in output
                    if template_file.name == env_workflow_file:
                        rest_of_path = Path(str(rest_of_path).replace(env_workflow_file, self.WORKFLOW_FILE_DEV))
                        logger.info(f"Renaming output file: {env_workflow_file} -> {self.WORKFLOW_FILE_DEV}")

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

        # Generate individual cronjob manifest files if cronjobs are provided
        if cronjobs and len(cronjobs) > 0:
            logger.info(f"=== Generating Individual CronJob Manifests ===")

            # Find the cronjob.yaml template
            cronjob_template_path = self.template_dir / "git-ops" / "templates" / "cronjob.yaml"

            if cronjob_template_path.exists():
                # Read the cronjob template
                with open(cronjob_template_path, 'r', encoding='utf-8') as f:
                    cronjob_template_content = f.read()

                # Output directory for cronjob manifests (same as other templates)
                cronjob_output_dir = self.output_base_dir / "git-ops" / microservice_name / "templates"

                # Convert cronjobs to list of dicts if they're Pydantic models
                cronjobs_list = [
                    cj.dict() if hasattr(cj, 'dict') else cj
                    for cj in cronjobs
                ]

                # Generate individual cronjob manifests
                cronjob_files = self.generate_cronjob_manifests(
                    cronjobs=cronjobs_list,
                    template_content=cronjob_template_content,
                    output_dir=cronjob_output_dir,
                    base_replacements=replacements
                )

                # Add generated cronjob files to processed files list
                processed_files.extend(cronjob_files)

                logger.info(f"Generated {len(cronjob_files)} individual cronjob manifest files")
            else:
                logger.warning(f"CronJob template not found at: {cronjob_template_path}")

        # Generate worker manifest file if worker is provided
        if worker:
            logger.info(f"=== Generating Worker Manifest ===")

            # Find the worker.yaml template
            worker_template_path = self.template_dir / "git-ops" / "templates" / "worker.yaml"

            if worker_template_path.exists():
                # Read the worker template
                with open(worker_template_path, 'r', encoding='utf-8') as f:
                    worker_template_content = f.read()

                # Output directory for worker manifest (same as other templates)
                worker_output_dir = self.output_base_dir / "git-ops" / microservice_name / "templates"

                # Convert worker to dict if it's a Pydantic model
                worker_dict = worker.dict() if hasattr(worker, 'dict') else worker

                # Generate worker manifest
                worker_files = self.generate_worker_manifest(
                    worker=worker_dict,
                    template_content=worker_template_content,
                    output_dir=worker_output_dir,
                    base_replacements=replacements
                )

                # Add generated worker file to processed files list
                processed_files.extend(worker_files)

                logger.info(f"Generated {len(worker_files)} worker manifest file")
            else:
                logger.warning(f"Worker template not found at: {worker_template_path}")

        # Generate Istio Gateway and VirtualService manifests for UAT environment only
        if environment.lower() == self.ENV_UAT:
            logger.info(f"=== Generating Istio Manifests for UAT Environment ===")

            # Output directory for Istio manifests (same as other templates)
            istio_output_dir = self.output_base_dir / "git-ops" / microservice_name / "templates"

            # Check for existing gateway.yaml template, otherwise generate dynamically
            gateway_template_path = self.template_dir / "git-ops" / "templates" / "gateway.yaml"

            if gateway_template_path.exists():
                # Use existing template
                logger.info(f"Found gateway template at: {gateway_template_path}")
                with open(gateway_template_path, 'r', encoding='utf-8') as f:
                    gateway_content = f.read()

                # Process content with replacements
                processed_gateway, gateway_replacement_count = self.process_file_content(
                    gateway_content, replacements
                )

                # Write processed content
                gateway_output_file = istio_output_dir / "gateway.yaml"
                istio_output_dir.mkdir(parents=True, exist_ok=True)
                with open(gateway_output_file, 'w', encoding='utf-8') as f:
                    f.write(processed_gateway)

                processed_files.append({
                    'source_path': str(gateway_template_path),
                    'output_path': str(gateway_output_file),
                    'replacements_made': gateway_replacement_count
                })
                logger.info(f"Generated gateway.yaml from template ({gateway_replacement_count} replacements)")
            else:
                # Generate dynamically
                logger.info("No gateway template found, generating dynamically")
                gateway_files = self.generate_gateway_manifest(
                    microservice_name=microservice_name,
                    domain_name=domain_name,
                    output_dir=istio_output_dir,
                    base_replacements=replacements
                )
                processed_files.extend(gateway_files)

            # Check for existing virtualservice.yaml template, otherwise generate dynamically
            virtualservice_template_path = self.template_dir / "git-ops" / "templates" / "virtualservice.yaml"

            if virtualservice_template_path.exists():
                # Use existing template
                logger.info(f"Found virtualservice template at: {virtualservice_template_path}")
                with open(virtualservice_template_path, 'r', encoding='utf-8') as f:
                    virtualservice_content = f.read()

                # Process content with replacements
                processed_virtualservice, vs_replacement_count = self.process_file_content(
                    virtualservice_content, replacements
                )

                # Write processed content
                virtualservice_output_file = istio_output_dir / "virtualservice.yaml"
                istio_output_dir.mkdir(parents=True, exist_ok=True)
                with open(virtualservice_output_file, 'w', encoding='utf-8') as f:
                    f.write(processed_virtualservice)

                processed_files.append({
                    'source_path': str(virtualservice_template_path),
                    'output_path': str(virtualservice_output_file),
                    'replacements_made': vs_replacement_count
                })
                logger.info(f"Generated virtualservice.yaml from template ({vs_replacement_count} replacements)")
            else:
                # Generate dynamically
                logger.info("No virtualservice template found, generating dynamically")
                virtualservice_files = self.generate_virtualservice_manifest(
                    microservice_name=microservice_name,
                    domain_name=domain_name,
                    container_port=container_port,
                    output_dir=istio_output_dir,
                    base_replacements=replacements
                )
                processed_files.extend(virtualservice_files)

            logger.info(f"=== Istio Manifests Generation Complete for UAT ===")
        else:
            logger.info(f"Skipping Istio manifests - environment '{environment}' is not UAT")

        logger.info(f"=== GitOps Template Processing Complete ===")
        logger.info(f"Total files processed: {len(processed_files)}")

        # Return human-readable replacement map (without {{ }})
        readable_replacements = {
            k.replace("{{", "").replace("}}", ""): v
            for k, v in replacements.items()
            # Exclude the formatted env var, cronjobs, and worker blocks from the simple variables list
            if k not in [
                self.PLACEHOLDER_ENVIRONMENT_VARIABLES,
                self.PLACEHOLDER_ENVIRONMENT_VARIABLES_YAML,
                self.PLACEHOLDER_ENVIRONMENT_VARIABLES_CONFIGMAP,
                self.PLACEHOLDER_CRONJOBS_YAML,
                self.PLACEHOLDER_CRONJOBS_COUNT,
                self.PLACEHOLDER_WORKER_YAML,
                self.PLACEHOLDER_WORKER_COUNT
            ]
        }

        return {
            'output_directory': str(self.output_base_dir),
            'processed_files': processed_files,
            'total_files_processed': len(processed_files),
            'template_variables': readable_replacements,
            'environment_variables': env_vars,
            'cronjobs': cronjobs,
            'worker': worker
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
