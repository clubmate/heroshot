"""
Configuration management for HeroShot
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for HeroShot"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_path: Path to configuration file (YAML or JSON)
        """
        self.config = {}
        self.config_path = config_path
        
        # Load default configuration
        self._load_default_config()
        
        # Load user configuration if provided
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
    
    def _load_default_config(self):
        """Load default configuration"""
        default_config_path = Path(__file__).parent.parent / "configs" / "config.yaml"
        if default_config_path.exists():
            with open(default_config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            # Fallback minimal config
            self.config = {
                'input': {'source': '', 'source_type': 'auto'},
                'output': {'base_directory': 'outputs', 'create_subdirectory': True},
                'scene_detection': {'enabled': True, 'threshold': 30.0},
                'hero_shot': {'enabled': True, 'scoring_method': 'combined'},
                'style_transformation': {'enabled': True},
                'video_reconstruction': {'enabled': True, 'frame_duration': 0.3},
                'logging': {'level': 'INFO', 'verbose': False},
                'performance': {'show_progress_bars': True}
            }
    
    def load_config(self, config_path: str):
        """
        Load configuration from file
        
        Args:
            config_path: Path to configuration file
        """
        try:
            with open(config_path, 'r') as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    user_config = yaml.safe_load(f)
                elif config_path.endswith('.json'):
                    user_config = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path}")
            
            # Merge with default config
            self._deep_merge(self.config, user_config)
            logger.info(f"Loaded configuration from {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            raise
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]):
        """
        Deep merge two dictionaries
        
        Args:
            base: Base dictionary to merge into
            update: Dictionary with updates
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'input.source')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'input.source')
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
    
    def override_from_args(self, args: Dict[str, Any]):
        """
        Override configuration with command line arguments
        
        Args:
            args: Dictionary of command line arguments
        """
        # Map CLI args to config keys
        arg_mapping = {
            'input_source': 'input.source',
            'output_dir': 'output.base_directory',
            'scene_threshold': 'scene_detection.threshold',
            'style_preset': 'style_transformation.generation.style_preset',
            'frame_duration': 'video_reconstruction.frame_duration',
            'verbose': 'logging.verbose',
        }
        
        for arg_key, config_key in arg_mapping.items():
            if arg_key in args and args[arg_key] is not None:
                self.set(config_key, args[arg_key])
    
    def save_config(self, output_path: str):
        """
        Save current configuration to file
        
        Args:
            output_path: Path to save configuration
        """
        try:
            with open(output_path, 'w') as f:
                if output_path.endswith('.yaml') or output_path.endswith('.yml'):
                    yaml.dump(self.config, f, default_flow_style=False, indent=2)
                elif output_path.endswith('.json'):
                    json.dump(self.config, f, indent=2)
                else:
                    raise ValueError(f"Unsupported config file format: {output_path}")
            
            logger.info(f"Saved configuration to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration to {output_path}: {e}")
            raise
    
    def validate(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if configuration is valid
        """
        required_keys = [
            'input.source',
            'output.base_directory',
        ]
        
        for key in required_keys:
            if self.get(key) is None:
                logger.error(f"Missing required configuration: {key}")
                return False
        
        return True
    
    def __str__(self) -> str:
        """String representation of configuration"""
        return yaml.dump(self.config, default_flow_style=False, indent=2)


# Global configuration instance
_config_instance = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def init_config(config_path: Optional[str] = None) -> Config:
    """
    Initialize global configuration
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration instance
    """
    global _config_instance
    _config_instance = Config(config_path)
    return _config_instance