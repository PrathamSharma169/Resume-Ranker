"""
In-Memory Cache Utility
Provides simple caching for expensive computations.
"""

from typing import Any, Optional
from src.utils.logger import get_logger

logger = get_logger("cache")


class Cache:
    """Simple in-memory cache with optional size limit."""

    def __init__(self, name: str = "default", max_items: int = 10000):
        self.name = name
        self.max_items = max_items
        self._store: dict[str, Any] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._store:
            self._hits += 1
            return self._store[key]
        self._misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        if len(self._store) >= self.max_items:
            # Remove oldest entry (FIFO eviction)
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]
        self._store[key] = value

    def has(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self._store

    def clear(self) -> None:
        """Clear all cache entries."""
        self._store.clear()
        self._hits = 0
        self._misses = 0

    @property
    def size(self) -> int:
        """Current number of cached items."""
        return len(self._store)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "name": self.name,
            "size": self.size,
            "max_items": self.max_items,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self.hit_rate:.2%}",
        }


# Global cache instances
_caches: dict[str, Cache] = {}


def get_cache(name: str = "default", max_items: int = 10000) -> Cache:
    """Get or create a named cache instance."""
    if name not in _caches:
        _caches[name] = Cache(name=name, max_items=max_items)
    return _caches[name]


def get_all_cache_stats() -> list[dict]:
    """Get statistics for all caches."""
    return [cache.stats() for cache in _caches.values()]
