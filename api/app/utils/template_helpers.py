"""
Template & Client Config Helpers

Reusable utilities for:
  - Reading template files from a directory
  - Loading per-client YAML configuration
  - Extracting environment-specific sections from configs
  - Replacing {{placeholder}} tokens in template content
  - Listing available templates

These are intentionally framework-agnostic so any service
(Terraform, GitOps, etc.) can import and use them.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.core.logging_config import logger


def read_template(
    template_dir: Path,
    name: str,
    extension: str = ".tf",
) -> str:
    """
    Read a template file from *template_dir*.

    Args:
        template_dir: Directory containing template files.
        name: Template name (without extension).
        extension: File extension including the dot (e.g. ".tf", ".yaml").

    Returns:
        Raw template content as a string.

    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    template_path = template_dir / f"{name}{extension}"

    if not template_path.exists():
        available = list_templates(template_dir, extension)
        raise FileNotFoundError(
            f"Template not found: {template_path}. "
            f"Available templates: {available}"
        )

    logger.info(f"Reading template: {template_path}")
    return template_path.read_text(encoding="utf-8")


def load_client_config(
    client_config_dir: Path,
    client_name: str,
) -> Dict[str, Any]:
    """
    Load and parse a per-client YAML configuration file.

    Expected path: ``<client_config_dir>/<client_name>.yaml``

    Args:
        client_config_dir: Directory containing client YAML files.
        client_name: Client identifier (used as the file stem).

    Returns:
        Parsed YAML content as a dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the file does not contain a YAML mapping.
    """
    config_path = client_config_dir / f"{client_name}.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Client configuration not found: {config_path}. "
            f"Expected file: client_config/{client_name}.yaml"
        )

    logger.info(f"Loading client config: {config_path}")
    with open(config_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid client config format in {config_path}: "
            "expected a YAML mapping at the top level"
        )
    return data


def extract_env_config(
    client_cfg: Dict[str, Any],
    section: str,
    environment: str,
    client_name: str = "",
) -> Dict[str, Any]:
    """
    Extract an environment-specific block from a client config.

    Navigates ``client_cfg[section][environment]`` and returns
    the resulting dict.

    Example YAML structure::

        gcp:          # <-- section
          dev:        # <-- environment
            project_id: "…"
            location: "…"

    Args:
        client_cfg: Full parsed client config dict.
        section: Top-level key to look up (e.g. "gcp", "argocd").
        environment: Sub-key under *section* (e.g. "dev", "prod").
        client_name: Used only in error messages for clarity.

    Returns:
        The environment-specific dict.

    Raises:
        KeyError: If *section* or *environment* is missing.
    """
    section_data = client_cfg.get(section)
    if not section_data or not isinstance(section_data, dict):
        raise KeyError(
            f"Client config for '{client_name}' is missing "
            f"the '{section}' section"
        )

    env_data = section_data.get(environment)
    if not env_data or not isinstance(env_data, dict):
        available = list(section_data.keys())
        raise KeyError(
            f"Environment '{environment}' not found under '{section}' "
            f"in client config for '{client_name}'. "
            f"Available environments: {available}"
        )

    return env_data


def render_template(
    template_content: str,
    replacements: Dict[str, str],
) -> str:
    """
    Replace ``{{placeholder}}`` tokens in *template_content*.

    Args:
        template_content: Raw template string.
        replacements: Mapping of placeholder (including braces) to value.

    Returns:
        Rendered string with all known placeholders replaced.
    """
    rendered = template_content
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def list_templates(
    template_dir: Path,
    extension: str = ".tf",
) -> List[str]:
    """
    Return the stem names of available template files.

    Args:
        template_dir: Directory to scan.
        extension: File extension to match (e.g. ".tf", ".yaml").

    Returns:
        Sorted list of template names (without extension).
    """
    if not template_dir.exists():
        return []
    return sorted(p.stem for p in template_dir.glob(f"*{extension}"))
