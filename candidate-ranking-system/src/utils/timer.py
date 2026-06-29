"""
Execution Timer Utility
Provides timing decorators and context managers for performance tracking.
"""

import time
import functools
from src.utils.logger import get_logger

logger = get_logger("timer")

# Global timing registry
_timings: dict[str, list[float]] = {}


class Timer:
    """Context manager for timing code blocks."""

    def __init__(self, name: str, log: bool = True):
        self.name = name
        self.log = log
        self.start_time = 0.0
        self.elapsed = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self.start_time
        if self.name not in _timings:
            _timings[self.name] = []
        _timings[self.name].append(self.elapsed)
        if self.log:
            logger.info(f"[{self.name}] completed in {self.elapsed:.3f}s")


def timed(func):
    """Decorator to time function execution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with Timer(func.__qualname__):
            return func(*args, **kwargs)
    return wrapper


def get_timings() -> dict[str, dict]:
    """Get all recorded timings with statistics."""
    result = {}
    for name, times in _timings.items():
        result[name] = {
            "total": sum(times),
            "count": len(times),
            "avg": sum(times) / len(times) if times else 0,
            "min": min(times) if times else 0,
            "max": max(times) if times else 0,
        }
    return result


def reset_timings():
    """Reset all timing records."""
    _timings.clear()
