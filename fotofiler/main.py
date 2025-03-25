"""
Main entry point for FotoFiler.
"""
import os
import sys
import logging
import argparse
import traceback
from typing import Dict, Any, Optional

from .core.logger import setup_logging
from .ui.cli import run_cli

def main():
    """Main entry point for the application."""
    try:
        # Set up logging
        log_dir = os.path.join(os.path.expanduser("~"), ".fotofiler", "logs")
        logger = setup_logging(log_dir=log_dir, console_level=logging.INFO)
        
        # Run the CLI
        run_cli()
        
    except KeyboardInterrupt:
        print("\nOperation canceled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
