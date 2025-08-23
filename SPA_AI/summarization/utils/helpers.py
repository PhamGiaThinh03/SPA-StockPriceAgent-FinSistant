import time
from functools import wraps
from typing import Callable, Any
from .logger import logger

def measure_performance(func: Callable) -> Callable:
    """Decorator to measure execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        logger.info(f"Function {func.__name__} executed in {elapsed:.2f} seconds")
        return result
    return wrapper