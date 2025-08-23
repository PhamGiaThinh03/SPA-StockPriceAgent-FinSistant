import logging
import sys
from typing import Optional

def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """Configure a professional logger"""
    logger = logging.getLogger(name or __name__)
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (uncomment to enable file logging)
    # file_handler = logging.FileHandler('summarization.log')
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()