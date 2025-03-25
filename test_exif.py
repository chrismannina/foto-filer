#!/usr/bin/env python3
"""
Test script to verify EXIF metadata extraction for FotoFiler.
This helps diagnose issues with the metadata extraction process.
"""
import os
import sys
import json
import subprocess
from datetime import datetime
import argparse

def run_exiftool(image_path):
    """Run exiftool on a single image and return the raw JSON output."""
    try:
        result = subprocess.run(
            ['exiftool', '-j', '-a', '-u', '-G1', image_path],
            check=True,
            capture_output=True,
            text=True
        )
        return json.loads(result.stdout)[0]
    except subprocess.SubprocessError as e:
        print(f"Error running exiftool: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing exiftool output: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("exiftool not found. Please install exiftool and ensure it's in your PATH.")
        sys.exit(1)

def process_metadata(raw_metadata, file_path):
    """Process and extract key metadata fields from the raw exiftool output."""
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
        'System:FileModifyDate'
    ]
    
    for field in date_fields:
        if field in raw_metadata and raw_metadata[field]:
            try:
                # Exiftool date format is typically: "YYYY:MM:DD HH:MM:SS"
                date_str = raw_metadata[field].split('+')[0].strip()  # Remove timezone if present
                date_str = date_str.split('-')[0].strip()  # Remove timezone offset if present
                date_taken = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                print(f"Date found in field: {field} = {date_str}")
                break
            except (ValueError, TypeError) as e:
                print(f"Error parsing date from {field}: {e}")
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
        print("WARNING: No date information found in the image metadata!")
    
    # Camera information
    camera_make = raw_metadata.get('IFD0:Make', '')
    camera_model = raw_metadata.get('IFD0:Model', '')
    print(f"Camera Make: {camera_make}")
    print(f"Camera Model: {camera_model}")
    
    processed.update({
        'camera_make': camera_make.replace(' ', '_'),
        'camera_model': camera_model.replace(' ', '_'),
        'camera': f"{camera_make}_{camera_model}".replace(' ', '_'),
    })
    
    # Lens information - check different possible field names
    lens_fields = ['ExifIFD:LensModel', 'ExifIFD:LensInfo', 'Composite:LensID', 'MakerNotes:Lens']
    lens = ''
    for field in lens_fields:
        if field in raw_metadata and raw_metadata[field]:
            lens = raw_metadata[field]
            break
    
    print(f"Lens: {lens}")
    processed['lens'] = lens.replace(' ', '_') if lens else ''
    
    # GPS information
    lat = raw_metadata.get('GPS:GPSLatitude') or raw_metadata.get('Composite:GPSLatitude')
    lon = raw_metadata.get('GPS:GPSLongitude') or raw_metadata.get('Composite:GPSLongitude')
    if lat and lon:
        print(f"GPS Coordinates: {lat}, {lon}")
        processed.update({
            'latitude': lat,
            'longitude': lon,
            'gps': f"{lat},{lon}"
        })
    else:
        print("No GPS data found")
    
    # Other useful EXIF data
    processed.update({
        'iso': raw_metadata.get('ExifIFD:ISO', ''),
        'aperture': raw_metadata.get('ExifIFD:FNumber', '') or raw_metadata.get('Composite:Aperture', ''),
        'focal_length': (raw_metadata.get('ExifIFD:FocalLength', '') or '').replace(' ', ''),
        'shutter_speed': raw_metadata.get('ExifIFD:ExposureTime', '') or raw_metadata.get('Composite:ShutterSpeed', ''),
    })
    
    return processed

def simulate_folder_path(metadata, hierarchy_pattern):
    """Simulate how the folder path would be generated based on the metadata."""
    if not hierarchy_pattern:
        return "Root destination folder (flat organization)"
    
    # Split the hierarchy pattern into segments
    hierarchy_segments = hierarchy_pattern.split('/')
    path_parts = []
    
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
                print(f"WARNING: Placeholder '{placeholder}' not found in metadata! Using 'unknown' instead.")
        
        path_parts.append(segment_value)
    
    return os.path.join("destination_root", *path_parts)

def test_filename_generation(metadata, naming_pattern):
    """Test how a filename would be generated based on the metadata."""
    import re
    
    # Find all placeholders in the pattern
    placeholder_regex = re.compile(r'{([^{}]+)}')
    placeholders = placeholder_regex.findall(naming_pattern)
    
    # Create a copy of the pattern for substitution
    new_filename = naming_pattern
    
    # Replace each placeholder with its value from metadata
    for placeholder in placeholders:
        if placeholder not in metadata or not str(metadata[placeholder]):
            print(f"WARNING: Placeholder '{placeholder}' not found in metadata for filename!")
            # Replace with empty string if metadata is missing
            value = ""
        else:
            value = str(metadata[placeholder])
        
        # Replace the placeholder in the pattern
        new_filename = new_filename.replace(f"{{{placeholder}}}", value)
    
    # Clean up the filename (remove invalid characters)
    invalid_chars = r'[<>:"/\\|?*]'
    clean_name = re.sub(invalid_chars, '_', new_filename)
    
    # Replace multiple underscores with a single one
    clean_name = re.sub(r'_+', '_', clean_name)
    
    # Remove leading/trailing underscores
    clean_name = clean_name.strip('_')
    
    # Add the extension
    if 'extension' in metadata and metadata['extension']:
        clean_name = f"{clean_name}.{metadata['extension']}"
    
    return clean_name

def main():
    parser = argparse.ArgumentParser(description="Test EXIF metadata extraction for FotoFiler")
    parser.add_argument("image_path", help="Path to the image file to test")
    parser.add_argument("--hierarchy", default="{year}/{month}/{day}", 
                     help="Folder hierarchy pattern to test (default: {year}/{month}/{day})")
    parser.add_argument("--naming", default="{date}_{camera}_{original_filename}",
                     help="Naming pattern to test (default: {date}_{camera}_{original_filename})")
    parser.add_argument("--dump", action="store_true", help="Dump all raw metadata fields")
    
    args = parser.parse_args()
    
    if not os.path.isfile(args.image_path):
        print(f"Error: The file {args.image_path} does not exist.")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"Testing EXIF metadata extraction for: {args.image_path}")
    print(f"{'='*60}\n")
    
    # Run exiftool and get raw metadata
    raw_metadata = run_exiftool(args.image_path)
    
    # Process the metadata
    print("\nExtracting key metadata fields:")
    print("-" * 40)
    processed_metadata = process_metadata(raw_metadata, args.image_path)
    
    # Show results
    print("\nProcessed Metadata:")
    print("-" * 40)
    for key, value in processed_metadata.items():
        if key not in ('file_path', 'file_size'):  # Skip verbose fields
            print(f"{key}: {value}")
    
    # Simulate folder path
    print("\nSimulated Folder Path:")
    print("-" * 40)
    print(f"Hierarchy Pattern: {args.hierarchy}")
    folder_path = simulate_folder_path(processed_metadata, args.hierarchy)
    print(f"Result: {folder_path}")
    
    # Test filename generation
    print("\nSimulated Filename:")
    print("-" * 40)
    print(f"Naming Pattern: {args.naming}")
    filename = test_filename_generation(processed_metadata, args.naming)
    print(f"Result: {filename}")
    
    # Full destination path
    print("\nFull Destination Path:")
    print("-" * 40)
    full_path = os.path.join(folder_path, filename)
    print(full_path)
    
    # Dump all metadata if requested
    if args.dump:
        print("\nAll Raw Metadata Fields:")
        print("-" * 40)
        for key, value in sorted(raw_metadata.items()):
            print(f"{key}: {value}")

if __name__ == "__main__":
    main() 