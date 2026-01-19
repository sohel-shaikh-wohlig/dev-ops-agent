import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from app.core.logging_config import logger


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
        Update values.yaml with new environment variables
        (Original: update_values_yaml)
        
        Args:
            env_vars: Environment variables to update
            values_data: Current values.yaml content
            
        Returns:
            Updated values.yaml content
        """
        if 'config' not in values_data:
            values_data['config'] = {}
        
        for key, value in env_vars.items():
            old_value = values_data['config'].get(key)
            
            if old_value != value:
                if old_value is None:
                    self.changes.append({
                        'file': 'values.yaml',
                        'type': 'ADD',
                        'key': key,
                        'old': None,
                        'new': value
                    })
                    logger.info(f"Adding new value in values.yaml: {key}={value}")
                else:
                    self.changes.append({
                        'file': 'values.yaml',
                        'type': 'UPDATE',
                        'key': key,
                        'old': str(old_value),
                        'new': value
                    })
                    logger.info(f"Updating value in values.yaml: {key} = {old_value} -> {value}")
                
                values_data['config'][key] = value
        
        return values_data
    
    def update_configmap_template(self, env_vars: Dict[str, str]) -> str:
        """
        Update configmap.yaml template with new variables
        (Original: update_configmap_template)
        
        Args:
            env_vars: Environment variables to update
            
        Returns:
            Updated configmap.yaml content as string
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
                # Update existing line
                pattern = rf'(\s*{key}:)\s*{{{{.*?}}}}'
                if re.search(pattern, content):
                    self.changes.append({
                        'file': 'configmap.yaml',
                        'type': 'UPDATE',
                        'key': key,
                        'old': 'existing template',
                        'new': template_value
                    })
                    logger.info(f"Updating configmap.yaml template: {key}")
                    updated_content = re.sub(pattern, rf'\1 {template_value}', updated_content)
            else:
                # Add new line
                self.changes.append({
                    'file': 'configmap.yaml',
                    'type': 'ADD',
                    'key': key,
                    'old': None,
                    'new': template_value
                })
                logger.info(f"Adding new entry to configmap.yaml: {key}")
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
    
    def apply_changes(self, env_vars: Dict[str, str]) -> List[Dict]:
        """
        Apply changes to configuration files
        
        Args:
            env_vars: Environment variables to apply
            
        Returns:
            List of changes that were applied
        """
        self.changes = []  # Reset changes
        
        # Validate structure
        is_valid, error_msg = self.validate_structure()
        if not is_valid:
            raise ValueError(error_msg)
        
        # Load and update values.yaml
        values_data = self.load_values_yaml()
        updated_values = self.update_values_yaml(env_vars, values_data)
        self.save_values_yaml(updated_values)
        
        # Update configmap.yaml
        updated_configmap = self.update_configmap_template(env_vars)
        with open(self.configmap_file, 'w') as f:
            f.write(updated_configmap)
        
        logger.info(f"Applied {len(self.changes)} changes successfully")
        return self.changes
    
    def get_changes_summary(self) -> Dict[str, int]:
        """
        Get summary of changes
        
        Returns:
            Dictionary with change counts
        """
        summary = {
            'total_changes': len(self.changes),
            'values_yaml_changes': len([c for c in self.changes if c['file'] == 'values.yaml']),
            'configmap_yaml_changes': len([c for c in self.changes if c['file'] == 'configmap.yaml']),
            'additions': len([c for c in self.changes if c['type'] == 'ADD']),
            'updates': len([c for c in self.changes if c['type'] == 'UPDATE'])
        }
        return summary