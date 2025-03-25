"""
Metadata extraction module for FotoFiler.
Uses exiftool to extract metadata from image files.
"""
import os
import json
import subprocess
from datetime import datetime
import logging
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

class MetadataExtractor:
    """Class to extract metadata from image files using exiftool."""
    
    def __init__(self, file_types: Optional[List[str]] = None):
        """
        Initialize the metadata extractor.
        
        Args:
            file_types: List of file extensions to process (e.g., ['jpg', 'png']).
                        If None, all supported extensions will be processed.
        """
        self.file_types = file_types or ['jpg', 'jpeg', 'png', 'nef', 'cr2', 'arw', 'tiff', 'tif', 'heic']
        self._check_exiftool()
    
    def _check_exiftool(self) -> None:
        """Check if exiftool is installed and available in the PATH."""
        try:
            subprocess.run(['exiftool', '-ver'], 
                          check=True, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
            logger.debug("Exiftool found and working")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error("Exiftool not found or not working properly: %s", e)
            raise RuntimeError("Exiftool is required but not found or not working properly. "
                             "Please install exiftool and ensure it's in your PATH.")
    
    def is_supported_file(self, filename: str) -> bool:
        """
        Check if the file is supported based on its extension.
        
        Args:
            filename: Name of the file to check.
            
        Returns:
            True if the file is supported, False otherwise.
        """
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        return ext in self.file_types
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a single file using exiftool.
        
        Args:
            file_path: Path to the image file.
            
        Returns:
            Dictionary containing the extracted metadata.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
            RuntimeError: If exiftool fails to extract metadata.
        """
        if not os.path.isfile(file_path):
            logger.error("File not found: %s", file_path)
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Run exiftool with JSON output for easy parsing
            result = subprocess.run(
                ['exiftool', '-j', '-a', '-u', '-G1', file_path],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Parse the JSON output
            metadata = json.loads(result.stdout)[0]
            
            # Process and standardize the metadata
            processed_metadata = self._process_metadata(metadata, file_path)
            return processed_metadata
            
        except subprocess.SubprocessError as e:
            logger.error("Exiftool failed to extract metadata from %s: %s", file_path, e)
            raise RuntimeError(f"Failed to extract metadata from {file_path}: {e}")
        except json.JSONDecodeError as e:
            logger.error("Failed to parse exiftool output for %s: %s", file_path, e)
            raise RuntimeError(f"Failed to parse exiftool output for {file_path}: {e}")
    
    def _process_metadata(self, raw_metadata: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """
        Process and standardize the raw metadata extracted by exiftool.
        
        Args:
            raw_metadata: The raw metadata dictionary from exiftool.
            file_path: The original file path.
            
        Returns:
            Processed and standardized metadata dictionary.
        """
        # Extract filename and extension
        filename = os.path.basename(file_path)
        base_name, extension = os.path.splitext(filename)
        extension = extension.lstrip('.')
        
        # Initialize processed metadata with basic file info
        processed = {
            'original_filename': base_name,
            'extension': extension.lower(),
            'file_path': file_path,
            'file_size': raw_metadata.get('File:FileSize', ''),
        }
        
        # Extract date information
        date_taken = None
        date_fields = [
            'ExifIFD:DateTimeOriginal', 
            'ExifIFD:CreateDate', 
            'ExifIFD:ModifyDate',
            'File:FileModifyDate',
            'System:FileModifyDate',
            'IFD0:ModifyDate'
        ]
        
        for field in date_fields:
            if field in raw_metadata and raw_metadata[field]:
                try:
                    # Exiftool date format is typically: "YYYY:MM:DD HH:MM:SS"
                    date_str = raw_metadata[field].split('+')[0].strip()  # Remove timezone if present
                    date_str = date_str.split('-')[0].strip()  # Remove timezone offset if present
                    date_taken = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    logger.debug("Date found in field %s: %s", field, date_str)
                    break
                except (ValueError, TypeError):
                    continue
        
        # Format date information if available
        if date_taken:
            processed.update({
                'date': date_taken.strftime("%Y-%m-%d"),
                'time': date_taken.strftime("%H-%M-%S"),
                'year': date_taken.strftime("%Y"),
                'month': date_taken.strftime("%m"),
                'day': date_taken.strftime("%d"),
                'hour': date_taken.strftime("%H"),
                'minute': date_taken.strftime("%M"),
                'second': date_taken.strftime("%S"),
                'datetime': date_taken.strftime("%Y%m%d_%H%M%S"),
            })
        else:
            logger.warning("No date information found for %s", file_path)
        
        # Camera information
        camera_make = raw_metadata.get('IFD0:Make', '')
        camera_model = raw_metadata.get('IFD0:Model', '')
        
        processed.update({
            'camera_make': camera_make.replace(' ', '_'),
            'camera_model': camera_model.replace(' ', '_'),
            'camera': f"{camera_make}_{camera_model}".replace(' ', '_'),
        })
        
        # Lens information - try multiple possible field names
        lens_fields = ['ExifIFD:LensModel', 'ExifIFD:LensInfo', 'Composite:LensID', 'MakerNotes:Lens']
        lens = ''
        for field in lens_fields:
            if field in raw_metadata and raw_metadata[field]:
                lens = raw_metadata[field]
                break
                
        processed['lens'] = lens.replace(' ', '_') if lens else ''
        
        # GPS information
        lat = raw_metadata.get('GPS:GPSLatitude') or raw_metadata.get('Composite:GPSLatitude')
        lon = raw_metadata.get('GPS:GPSLongitude') or raw_metadata.get('Composite:GPSLongitude')
        if lat and lon:
            processed.update({
                'latitude': lat,
                'longitude': lon,
                'gps': f"{lat},{lon}"
            })
        
        # Other useful EXIF data
        processed.update({
            'iso': raw_metadata.get('ExifIFD:ISO', ''),
            'aperture': raw_metadata.get('ExifIFD:FNumber', '') or raw_metadata.get('Composite:Aperture', ''),
            'focal_length': (raw_metadata.get('ExifIFD:FocalLength', '') or '').replace(' ', ''),
            'shutter_speed': raw_metadata.get('ExifIFD:ExposureTime', '') or raw_metadata.get('Composite:ShutterSpeed', ''),
        })
        
        return processed
    
    def scan_directory(self, directory: str) -> List[Dict[str, Any]]:
        """
        Scan a directory for image files and extract metadata from each.
        
        Args:
            directory: The directory to scan.
            
        Returns:
            List of dictionaries containing metadata for each image file.
            
        Raises:
            FileNotFoundError: If the directory doesn't exist.
        """
        if not os.path.isdir(directory):
            logger.error("Directory not found: %s", directory)
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        logger.info("Scanning directory: %s", directory)
        
        results = []
        errors = []
        
        # Walk through the directory
        for root, _, files in os.walk(directory):
            for file in files:
                if not self.is_supported_file(file):
                    continue
                
                file_path = os.path.join(root, file)
                try:
                    metadata = self.extract_metadata(file_path)
                    results.append(metadata)
                    logger.debug("Extracted metadata from: %s", file_path)
                except Exception as e:
                    logger.warning("Failed to extract metadata from %s: %s", file_path, e)
                    errors.append((file_path, str(e)))
        
        if errors:
            logger.warning("Failed to extract metadata from %d files", len(errors))
        
        logger.info("Successfully extracted metadata from %d files", len(results))
        return results
