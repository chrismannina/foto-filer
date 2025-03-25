"""
Organization module for FotoFiler.
Handles folder structure creation and file organization based on metadata.
"""
import os
import shutil
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class OrganizationEngine:
    """Class to organize files into folders based on metadata and hierarchy patterns."""
    
    # Common hierarchy templates
    HIERARCHY_TEMPLATES = {
        "flat": "",  # No subdirectories
        "date": "{year}/{month}/{day}",
        "year_month": "{year}/{month}",
        "year": "{year}",
        "camera": "{camera}",
        "camera_date": "{camera}/{year}/{month}/{day}",
        "year_camera": "{year}/{camera}"
    }
    
    def __init__(self, destination: str, hierarchy: Optional[str] = None):
        """
        Initialize the organization engine.
        
        Args:
            destination: Base destination directory.
            hierarchy: Folder hierarchy pattern, with placeholders in curly braces.
                       Example: "{year}/{month}/{day}"
                       Can also be one of the predefined templates keys.
                       If None, the "flat" hierarchy (no subdirectories) will be used.
        """
        self.destination = os.path.abspath(destination)
        
        # Determine the hierarchy pattern to use
        if hierarchy is None or hierarchy == "flat":
            self.hierarchy_pattern = ""
        elif hierarchy in self.HIERARCHY_TEMPLATES:
            self.hierarchy_pattern = self.HIERARCHY_TEMPLATES[hierarchy]
        else:
            self.hierarchy_pattern = hierarchy
        
        logger.info("Destination directory: %s", self.destination)
        logger.info("Hierarchy pattern: %s", self.hierarchy_pattern)
    
    def _ensure_directory_exists(self, directory: str) -> None:
        """
        Ensure that a directory exists, creating it if necessary.
        
        Args:
            directory: The directory path to ensure exists.
        """
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.debug("Created directory: %s", directory)
    
    def determine_destination_path(self, metadata: Dict[str, Any]) -> str:
        """
        Determine the destination path for a file based on its metadata and the hierarchy pattern.
        
        Args:
            metadata: The metadata dictionary for the file.
            
        Returns:
            The destination directory path.
        """
        # Start with the base destination
        dest_path = self.destination
        
        # If no hierarchy pattern, return the base destination
        if not self.hierarchy_pattern:
            return dest_path
        
        # Split the hierarchy pattern into segments
        hierarchy_segments = self.hierarchy_pattern.split('/')
        
        # Process each segment
        for segment in hierarchy_segments:
            if not segment:
                continue
                
            # Replace placeholders with metadata values
            segment_value = segment
            
            # Find all placeholders like {year}, {month}, etc.
            import re
            placeholders = re.findall(r'{([^{}]+)}', segment)
            
            for placeholder in placeholders:
                if placeholder in metadata and metadata[placeholder]:
                    # Replace the placeholder with its value
                    value = str(metadata[placeholder])
                    segment_value = segment_value.replace(f"{{{placeholder}}}", value)
                else:
                    # If metadata is missing, use "unknown"
                    segment_value = segment_value.replace(f"{{{placeholder}}}", "unknown")
            
            # Add the segment to the destination path
            dest_path = os.path.join(dest_path, segment_value)
        
        return dest_path
    
    def organize_file(self, source_path: str, metadata: Dict[str, Any], new_filename: str, 
                      dry_run: bool = False, move: bool = True) -> Tuple[str, str]:
        """
        Organize a single file based on metadata and hierarchy pattern.
        
        Args:
            source_path: Path to the source file.
            metadata: Metadata for the file.
            new_filename: The new filename (without path).
            dry_run: If True, don't actually move/copy the file, just simulate.
            move: If True, move the file; if False, copy the file.
            
        Returns:
            A tuple of (source_path, destination_path).
            In dry_run mode, destination_path is the path that would be used.
            
        Raises:
            FileNotFoundError: If the source file doesn't exist.
            PermissionError: If there are permission issues.
            OSError: For other file operation errors.
        """
        if not os.path.isfile(source_path):
            logger.error("Source file not found: %s", source_path)
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Determine destination directory
        dest_dir = self.determine_destination_path(metadata)
        
        # Create full destination path with new filename
        dest_path = os.path.join(dest_dir, new_filename)
        
        # Handle duplicate filenames
        from .naming import NamingEngine
        dest_path = NamingEngine().handle_duplicates(dest_path)
        
        # Log the operation
        operation = "Moving" if move else "Copying"
        logger.info("%s: %s -> %s%s", 
                  operation, source_path, dest_path, 
                  " (dry run)" if dry_run else "")
        
        # In dry run mode, just return the paths
        if dry_run:
            return source_path, dest_path
        
        # Create destination directory if it doesn't exist
        self._ensure_directory_exists(dest_dir)
        
        # Move or copy the file
        try:
            if move:
                shutil.move(source_path, dest_path)
            else:
                shutil.copy2(source_path, dest_path)
        except (PermissionError, OSError) as e:
            logger.error("Failed to %s file: %s -> %s: %s", 
                       "move" if move else "copy", source_path, dest_path, e)
            raise
        
        return source_path, dest_path
    
    def organize_files(self, files_metadata: List[Dict[str, Any]], new_filenames: List[str],
                      dry_run: bool = False, move: bool = True) -> List[Tuple[str, str]]:
        """
        Organize multiple files based on their metadata and hierarchy pattern.
        
        Args:
            files_metadata: List of metadata dictionaries for the files.
            new_filenames: List of new filenames (without paths).
            dry_run: If True, don't actually move/copy the files, just simulate.
            move: If True, move the files; if False, copy the files.
            
        Returns:
            List of tuples of (source_path, destination_path).
        """
        if len(files_metadata) != len(new_filenames):
            raise ValueError("Length of files_metadata and new_filenames must match")
        
        results = []
        
        for metadata, new_filename in zip(files_metadata, new_filenames):
            source_path = metadata['file_path']
            try:
                result = self.organize_file(source_path, metadata, new_filename, dry_run, move)
                results.append(result)
            except Exception as e:
                logger.error("Failed to organize file %s: %s", source_path, e)
                results.append((source_path, str(e)))
        
        return results
