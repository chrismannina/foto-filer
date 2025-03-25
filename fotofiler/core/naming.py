"""
Naming engine for FotoFiler.
Handles file renaming based on metadata and user-defined patterns.
"""
import os
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class NamingEngine:
    """Class to generate new filenames using metadata and patterns."""
    
    # Default pattern if none is specified
    DEFAULT_PATTERN = "{datetime}_{original_filename}"
    
    def __init__(self, pattern: Optional[str] = None):
        """
        Initialize the naming engine.
        
        Args:
            pattern: The naming pattern to use, with placeholders in curly braces.
                     Example: "{date}_{camera}_{original_filename}"
                     If None, the default pattern will be used.
        """
        self.pattern = pattern or self.DEFAULT_PATTERN
        self._validate_pattern(self.pattern)
        
        # Compiled regex to find placeholders like {date}, {camera}, etc.
        self.placeholder_regex = re.compile(r'{([^{}]+)}')
    
    def _validate_pattern(self, pattern: str) -> None:
        """
        Validate that the pattern has a valid format.
        
        Args:
            pattern: The pattern to validate.
            
        Raises:
            ValueError: If the pattern has invalid format or missing required placeholders.
        """
        if not pattern:
            raise ValueError("Naming pattern cannot be empty")
        
        # Check for unbalanced braces
        if pattern.count('{') != pattern.count('}'):
            raise ValueError("Naming pattern has unbalanced braces")
        
        # All placeholders should be in the format {name}
        if not re.match(r'^[^{}]*({\w+}[^{}]*)*$', pattern):
            raise ValueError("Naming pattern has invalid placeholder format")
        
        logger.debug("Naming pattern validated: %s", pattern)
    
    def generate_filename(self, metadata: Dict[str, Any]) -> str:
        """
        Generate a new filename based on the pattern and metadata.
        
        Args:
            metadata: Dictionary containing metadata fields to use in the filename.
            
        Returns:
            The new filename (without path).
            
        Raises:
            ValueError: If a required placeholder is missing in the metadata.
        """
        # Find all placeholders in the pattern
        placeholders = self.placeholder_regex.findall(self.pattern)
        
        # Create a copy of the pattern for substitution
        new_filename = self.pattern
        
        # Replace each placeholder with its value from metadata
        for placeholder in placeholders:
            if placeholder not in metadata or not str(metadata[placeholder]):
                logger.warning("Placeholder '%s' not found in metadata or empty", placeholder)
                # Replace with empty string if metadata is missing
                value = ""
            else:
                value = str(metadata[placeholder])
            
            # Replace the placeholder in the pattern
            new_filename = new_filename.replace(f"{{{placeholder}}}", value)
        
        # Clean up the filename (remove invalid characters)
        new_filename = self._clean_filename(new_filename)
        
        # Add the extension
        if 'extension' in metadata and metadata['extension']:
            new_filename = f"{new_filename}.{metadata['extension']}"
        
        return new_filename
    
    def _clean_filename(self, filename: str) -> str:
        """
        Clean a filename by removing invalid characters and handling empty segments.
        
        Args:
            filename: The filename to clean.
            
        Returns:
            A cleaned filename safe for use in file systems.
        """
        # Replace invalid characters with underscores
        invalid_chars = r'[<>:"/\\|?*]'
        clean_name = re.sub(invalid_chars, '_', filename)
        
        # Replace multiple underscores with a single one
        clean_name = re.sub(r'_+', '_', clean_name)
        
        # Remove leading/trailing underscores
        clean_name = clean_name.strip('_')
        
        # Handle empty filename case
        if not clean_name:
            clean_name = "unnamed_file"
        
        return clean_name
    
    def handle_duplicates(self, filepath: str) -> str:
        """
        Handle duplicate filenames by appending a number if necessary.
        
        Args:
            filepath: The complete filepath to check for duplicates.
            
        Returns:
            A filepath that doesn't exist yet by appending a number if necessary.
        """
        if not os.path.exists(filepath):
            return filepath
        
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)
        
        counter = 1
        new_filepath = filepath
        
        while os.path.exists(new_filepath):
            new_name = f"{name}_{counter}{ext}"
            new_filepath = os.path.join(directory, new_name)
            counter += 1
        
        logger.info("Resolved duplicate: %s -> %s", filepath, new_filepath)
        return new_filepath
