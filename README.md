# FotoFiler

A powerful and flexible photo organization tool that leverages exiftool to extract metadata, then renames and organizes your pictures based on user-defined rules.

## Features

- Extract detailed metadata from images using exiftool
- Rename files using customizable patterns with metadata placeholders
- Organize photos into flexible folder hierarchies
- Preview changes before execution (dry-run mode)
- Detailed logging and error handling

## Requirements

- Python 3.8+
- exiftool (must be installed and available in PATH)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/foto-filer.git
cd foto-filer

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Basic usage
python -m fotofiler.main --source /path/to/photos --dest /path/to/destination

# With custom naming pattern
python -m fotofiler.main --source /path/to/photos --dest /path/to/destination --pattern "{date}_{camera}_{original_filename}"

# Dry run (preview only)
python -m fotofiler.main --source /path/to/photos --dest /path/to/destination --dry-run

# Custom folder organization
python -m fotofiler.main --source /path/to/photos --dest /path/to/destination --hierarchy "year/month/day"
```

## Configuration

You can create a YAML configuration file for more advanced settings:

```yaml
source: /path/to/photos
destination: /path/to/destination
naming_pattern: "{date}_{camera}_{original_filename}"
folder_hierarchy: "year/month/day"
file_types: ["jpg", "jpeg", "png", "nef", "cr2", "arw"]
backup: true
```

Then use it with:

```bash
python -m fotofiler.main --config config.yaml
```

## License

MIT
