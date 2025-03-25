"""
Configuration module for FotoFiler.
Handles loading and validating user configuration from files or command-line arguments.
"""
import os
import yaml
import logging
import argparse
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

class Config:
    """Class to handle configuration loading and validation."""
    
    # Default configuration values
    DEFAULT_CONFIG = {
        "source": "",
        "destination": "",
        "naming_pattern": "{datetime}_{original_filename}",
        "folder_hierarchy": "flat",
        "file_types": ["jpg", "jpeg", "png", "nef", "cr2", "arw", "tiff", "tif", "heic"],
        "move": True,
        "backup": False,
        "recursive": True,
        "dry_run": False
    }
    
    def __init__(self, config_path: Optional[str] = None, cli_args: Optional[Dict[str, Any]] = None):
        """
        Initialize the configuration.
        
        Args:
            config_path: Path to a YAML configuration file.
            cli_args: Command-line arguments as a dictionary.
                      These will override configuration file settings.
        """
        # Start with default config
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Load configuration file if provided
        if config_path:
            self._load_config_file(config_path)
        
        # Override with command-line arguments if provided
        if cli_args:
            self._apply_cli_args(cli_args)
        
        # Validate the configuration
        self._validate_config()
        
        logger.info("Configuration loaded")
    
    def _load_config_file(self, config_path: str) -> None:
        """
        Load configuration from a YAML file.
        
        Args:
            config_path: Path to the configuration file.
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
            ValueError: If the configuration file has invalid format.
        """
        if not os.path.isfile(config_path):
            logger.error("Configuration file not found: %s", config_path)
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
            
            if not isinstance(file_config, dict):
                raise ValueError("Configuration file must contain a YAML dictionary")
            
            # Update configuration with file values
            self.config.update(file_config)
            logger.debug("Loaded configuration from file: %s", config_path)
            
        except yaml.YAMLError as e:
            logger.error("Error parsing configuration file: %s", e)
            raise ValueError(f"Error parsing configuration file: {e}")
    
    def _apply_cli_args(self, cli_args: Dict[str, Any]) -> None:
        """
        Apply command-line arguments to the configuration.
        
        Args:
            cli_args: Dictionary of command-line arguments.
        """
        # Only update non-None values
        for key, value in cli_args.items():
            if value is not None:
                self.config[key] = value
        
        logger.debug("Applied command-line arguments")
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid.
        """
        # Source directory must be specified and exist
        if not self.config.get("source"):
            raise ValueError("Source directory must be specified")
        
        if not os.path.isdir(self.config["source"]):
            raise ValueError(f"Source directory does not exist: {self.config['source']}")
        
        # Destination directory must be specified
        if not self.config.get("destination"):
            # If not specified, use the source directory
            self.config["destination"] = self.config["source"]
            logger.info("Using source directory as destination: %s", self.config["source"])
        
        # File types must be a list
        if not isinstance(self.config.get("file_types", []), list):
            raise ValueError("file_types must be a list")
        
        logger.debug("Configuration validated")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: The configuration key.
            default: Default value to return if the key is not found.
            
        Returns:
            The configuration value, or the default if not found.
        """
        return self.config.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """
        Get a configuration value using dictionary syntax.
        
        Args:
            key: The configuration key.
            
        Returns:
            The configuration value.
            
        Raises:
            KeyError: If the key is not found.
        """
        return self.config[key]
    
    def as_dict(self) -> Dict[str, Any]:
        """
        Get the entire configuration as a dictionary.
        
        Returns:
            Dictionary of all configuration values.
        """
        return self.config.copy()
    
    @staticmethod
    def parse_command_line() -> Dict[str, Any]:
        """
        Parse command-line arguments.
        
        Returns:
            Dictionary of command-line arguments.
        """
        parser = argparse.ArgumentParser(description="FotoFiler - Photo organization tool")
        
        parser.add_argument("--config", help="Path to configuration file")
        parser.add_argument("--source", help="Source directory containing photos")
        parser.add_argument("--dest", "--destination", dest="destination", 
                         help="Destination directory for organized photos")
        parser.add_argument("--pattern", "--naming-pattern", dest="naming_pattern", 
                         help="Naming pattern for files, e.g. '{date}_{camera}_{original_filename}'")
        parser.add_argument("--hierarchy", "--folder-hierarchy", dest="folder_hierarchy", 
                         help="Folder hierarchy pattern, e.g. 'year/month/day' or custom pattern")
        parser.add_argument("--move", action="store_true", help="Move files instead of copying")
        parser.add_argument("--copy", action="store_true", help="Copy files instead of moving")
        parser.add_argument("--backup", action="store_true", help="Create backups of files")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
        parser.add_argument("--recursive", action="store_true", help="Scan directories recursively")
        parser.add_argument("--no-recursive", action="store_false", dest="recursive", 
                         help="Don't scan directories recursively")
        
        args = parser.parse_args()
        
        # Convert args to dictionary
        cli_args = vars(args)
        
        # Handle --copy flag (it should set move=False)
        if cli_args.get("copy"):
            cli_args["move"] = False
            del cli_args["copy"]
        
        return cli_args
