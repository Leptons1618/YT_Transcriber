import logging
import os
import sys
import traceback
import time
from functools import wraps

# Configure logging
def setup_debug_logging():
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    debug_logger = logging.getLogger('debug')
    debug_logger.setLevel(logging.DEBUG)
    
    # Log to file with timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f'debug_{timestamp}.log')
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Format
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    debug_logger.addHandler(file_handler)
    debug_logger.addHandler(console_handler)
    
    return debug_logger

debug_logger = setup_debug_logging()

# Decorator for tracing function calls
def trace_function(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        debug_logger.info(f"ENTER {func.__name__} - Args: {args}, Kwargs: {kwargs}")
        try:
            result = func(*args, **kwargs)
            debug_logger.info(f"EXIT {func.__name__} - Result: {result}")
            return result
        except Exception as e:
            debug_logger.error(f"ERROR in {func.__name__}: {str(e)}")
            debug_logger.error(traceback.format_exc())
            raise
    return wrapper

# Function to log detailed environment information
def log_environment_info():
    debug_logger.info("=== Environment Information ===")
    debug_logger.info(f"Python version: {sys.version}")
    debug_logger.info(f"Platform: {sys.platform}")
    
    # Log available packages
    try:
        import pkg_resources
        installed_packages = sorted([f"{pkg.key}=={pkg.version}" 
                                   for pkg in pkg_resources.working_set])
        debug_logger.info(f"Installed packages: {', '.join(installed_packages)}")
    except ImportError:
        debug_logger.warning("Could not log installed packages")
    
    # Log environment variables (excluding sensitive information)
    debug_logger.info("Environment variables:")
    for key, value in os.environ.items():
        if not any(sensitive in key.lower() for sensitive in ['key', 'secret', 'token', 'password']):
            debug_logger.info(f"  {key}: {value}")
        else:
            debug_logger.info(f"  {key}: [REDACTED]")
    
    debug_logger.info("================================")
