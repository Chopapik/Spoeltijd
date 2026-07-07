"""Minimal cache store abstractions.

The default store is intentionally a no-op. It gives the proxy flow a cache
hook without changing runtime behavior or writing to the SD card yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Protocol

from .cache_key import CacheKey


@dataclass
class CachedResponse:
    status_code: int
    headers: Dict[str, str]
    content: bytes
    reason: str = "OK"


class CacheStore(Protocol):
    def get(self, key: CacheKey) -> Optional[CachedResponse]:
        ...

    def set(self, key: CacheKey, response: CachedResponse) -> None:
        ...


class NoOpCacheStore:
    """Disabled cache implementation used by default."""

    def get(self, key: CacheKey) -> Optional[CachedResponse]:
        return None

    def set(self, key: CacheKey, response: CachedResponse) -> None:
        return None


class MemoryCacheStore:
    """Small in-memory store useful for local experiments and future tests."""

    def __init__(self) -> None:
        self._responses: Dict[CacheKey, CachedResponse] = {}

    def get(self, key: CacheKey) -> Optional[CachedResponse]:
        return self._responses.get(key)

    def set(self, key: CacheKey, response: CachedResponse) -> None:
        self._responses[key] = response
