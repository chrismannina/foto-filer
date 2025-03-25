"""
Logging module for FotoFiler.
Configures logging functionality for the application.
"""
import os
import logging
import logging.handlers
from typing import Optional, Union
import datetime

def setup_logging(log_dir: Optional[str] = None, 
                 log_level: Union[int, str] = logging.INFO, 
                 console_level: Union[int, str] = logging.INFO) -> logging.Logger:
    """
    Set up logging for the application.
    
    Args:
        log_dir: Directory to save log files. If None, logs will only go to console.
        log_level: Logging level for file logs.
        console_level: Logging level for console output.
        
    Returns:
        The configured root logger.
    """
    # Get the root logger
    logger = logging.getLogger()
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Set the root logger level to the most verbose level we'll use
    logger.setLevel(min(logging.getLevelName(log_level) if isinstance(log_level, str) else log_level,
                       logging.getLevelName(console_level) if isinstance(console_level, str) else console_level))
    
    # Create formatters
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if log_dir is specified
    if log_dir:
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"fotofiler_{timestamp}.log")
        
        # Add a file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        logger.info("Logging to file: %s", log_file)
    
    return logger

def get_tqdm_compatible_logger(name: str = "fotofiler") -> logging.Logger:
    """
    Get a logger that's compatible with tqdm progress bars.
    
    This logger uses sys.stderr for output to avoid interfering with tqdm's progress bars.
    
    Args:
        name: The name for the logger.
        
    Returns:
        A configured logger.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Only add a handler if one doesn't exist
        import sys
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(handler)
    
    return logger

def log_error_and_continue(func):
    """
    Decorator to log errors but continue execution.
    
    Args:
        func: The function to decorate.
        
    Returns:
        The decorated function.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger(func.__module__)
            logger.error("Error in %s: %s", func.__name__, e, exc_info=True)
            return None
    return wrapper
