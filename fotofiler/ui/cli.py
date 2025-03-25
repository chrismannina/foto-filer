"""
Command-line interface for FotoFiler.
Handles user interaction in the terminal.
"""
import os
import sys
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from tqdm import tqdm

from ..core.metadata import MetadataExtractor
from ..core.naming import NamingEngine
from ..core.organization import OrganizationEngine
from ..core.config import Config
from ..core.logger import get_tqdm_compatible_logger

logger = get_tqdm_compatible_logger(__name__)

class CLI:
    """Command-line interface for FotoFiler."""
    
    def __init__(self, config: Config):
        """
        Initialize the CLI.
        
        Args:
            config: The application configuration.
        """
        self.config = config
    
    def run(self) -> None:
        """Run the FotoFiler application with CLI interface."""
        # Display welcome message
        self._display_header()
        
        # Display configuration summary
        self._display_config()
        
        # If dry run, show what would be done
        if self.config.get("dry_run"):
            print("\nRunning in DRY RUN mode - no files will be modified.")
        
        # Confirm before proceeding
        if not self._confirm_action():
            print("\nOperation canceled.")
            sys.exit(0)
        
        # Execute the organization process
        self._execute()
    
    def _display_header(self) -> None:
        """Display the application header."""
        print("\n" + "="*60)
        print("FotoFiler - Photo Organization Tool")
        print("="*60)
    
    def _display_config(self) -> None:
        """Display the current configuration."""
        config = self.config.as_dict()
        
        print("\nConfiguration:")
        print(f"  Source directory: {config['source']}")
        print(f"  Destination directory: {config['destination']}")
        print(f"  Naming pattern: {config['naming_pattern']}")
        print(f"  Folder hierarchy: {config['folder_hierarchy']}")
        print(f"  File operation: {'Move' if config['move'] else 'Copy'}")
        print(f"  Recursive scan: {'Yes' if config['recursive'] else 'No'}")
        if config['backup']:
            print(f"  Backup: Enabled")
    
    def _confirm_action(self) -> bool:
        """
        Ask the user to confirm the action.
        
        Returns:
            True if the user confirms, False otherwise.
        """
        while True:
            response = input("\nProceed with organization? [y/n]: ").lower()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' or 'n'.")
    
    def _execute(self) -> None:
        """Execute the photo organization process."""
        try:
            # Step 1: Scan source directory for photos
            print("\nScanning for photos...")
            metadata_extractor = MetadataExtractor(file_types=self.config.get("file_types"))
            all_metadata = metadata_extractor.scan_directory(self.config.get("source"))
            
            if not all_metadata:
                print("No photos found in the source directory.")
                return
            
            print(f"Found {len(all_metadata)} photos.")
            
            # Step 2: Generate new filenames
            print("\nGenerating new filenames...")
            naming_engine = NamingEngine(pattern=self.config.get("naming_pattern"))
            new_filenames = []
            
            for metadata in tqdm(all_metadata, desc="Generating filenames"):
                new_filename = naming_engine.generate_filename(metadata)
                new_filenames.append(new_filename)
            
            # Step 3: Organize files
            print("\nOrganizing files...")
            organization_engine = OrganizationEngine(
                destination=self.config.get("destination"),
                hierarchy=self.config.get("folder_hierarchy")
            )
            
            # Preview changes
            if self.config.get("dry_run"):
                self._preview_changes(all_metadata, new_filenames, organization_engine)
                return
            
            # Execute changes
            results = []
            move = self.config.get("move", True)
            
            for i, (metadata, new_filename) in enumerate(tqdm(zip(all_metadata, new_filenames), 
                                                         total=len(all_metadata), 
                                                         desc="Organizing")):
                try:
                    source_path = metadata['file_path']
                    result = organization_engine.organize_file(
                        source_path,
                        metadata,
                        new_filename,
                        dry_run=False,
                        move=move
                    )
                    results.append(result)
                except Exception as e:
                    logger.error("Failed to organize file %s: %s", metadata['file_path'], e)
                    results.append((metadata['file_path'], str(e)))
            
            # Step 4: Display summary
            self._display_summary(results)
            
        except Exception as e:
            logger.error("Error during execution: %s", e, exc_info=True)
            print(f"\nError: {e}")
            sys.exit(1)
    
    def _preview_changes(self, all_metadata: List[Dict[str, Any]], 
                        new_filenames: List[str],
                        organization_engine: OrganizationEngine) -> None:
        """
        Preview the changes that would be made.
        
        Args:
            all_metadata: List of metadata dictionaries for all files.
            new_filenames: List of new filenames.
            organization_engine: The organization engine.
        """
        print("\nPreview of changes (DRY RUN):")
        print("="*60)
        
        # Limit preview to 10 files if there are many
        preview_limit = 10
        show_limit = min(preview_limit, len(all_metadata))
        
        for i in range(show_limit):
            metadata = all_metadata[i]
            new_filename = new_filenames[i]
            source_path = metadata['file_path']
            
            # Get destination path
            dest_dir = organization_engine.determine_destination_path(metadata)
            dest_path = os.path.join(dest_dir, new_filename)
            
            operation = "Move" if self.config.get("move", True) else "Copy"
            print(f"{operation}: {source_path}")
            print(f"   -> {dest_path}")
            print("-"*60)
        
        if len(all_metadata) > preview_limit:
            print(f"... and {len(all_metadata) - preview_limit} more files")
        
        print("\nThis is a DRY RUN - no files were actually modified.")
    
    def _display_summary(self, results: List[Tuple[str, str]]) -> None:
        """
        Display a summary of the organization process.
        
        Args:
            results: List of (source_path, destination_path) tuples.
        """
        print("\nSummary:")
        print("="*60)
        
        success_count = 0
        error_count = 0
        
        for source, dest in results:
            if isinstance(dest, str) and os.path.exists(dest):
                success_count += 1
            else:
                error_count += 1
        
        operation = "Moved" if self.config.get("move", True) else "Copied"
        print(f"Total files processed: {len(results)}")
        print(f"Successfully {operation.lower()}: {success_count}")
        if error_count:
            print(f"Failed: {error_count}")
        
        print("\nOperation completed successfully.")

def run_cli() -> None:
    """Run the CLI application."""
    try:
        # Parse command-line arguments
        cli_args = Config.parse_command_line()
        
        # Load configuration
        config = Config(config_path=cli_args.get("config"), cli_args=cli_args)
        
        # Run the CLI
        cli = CLI(config)
        cli.run()
        
    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)
