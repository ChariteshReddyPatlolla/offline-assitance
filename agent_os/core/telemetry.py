import logging
from pythonjsonlogger import jsonlogger
import time
from functools import wraps
from typing import Dict, Any

class Telemetry:
    """
    Handles structured logging, metrics aggregation, and performance profiling.
    """
    _metrics: Dict[str, float] = {}

    @staticmethod
    def setup_structured_logging():
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        # Clear existing handlers
        if logger.hasHandlers():
            logger.handlers.clear()

        logHandler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)
        return logger

    @staticmethod
    def record_metric(name: str, value: float):
        if name not in Telemetry._metrics:
            Telemetry._metrics[name] = 0.0
        Telemetry._metrics[name] += value

    @staticmethod
    def get_metrics() -> Dict[str, float]:
        return Telemetry._metrics

    @staticmethod
    def profile(func):
        """Decorator to profile execution time of functions."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            
            elapsed = end_time - start_time
            Telemetry.record_metric(f"{func.__name__}_execution_time", elapsed)
            
            logger = logging.getLogger(__name__)
            logger.info("Profiler", extra={"function": func.__name__, "execution_time_s": elapsed})
            return result
        return wrapper

    @staticmethod
    def profile_async(func):
        """Decorator to profile execution time of async functions."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = await func(*args, **kwargs)
            end_time = time.perf_counter()
            
            elapsed = end_time - start_time
            Telemetry.record_metric(f"{func.__name__}_execution_time", elapsed)
            
            logger = logging.getLogger(__name__)
            logger.info("Profiler", extra={"function": func.__name__, "execution_time_s": elapsed})
            return result
        return wrapper
