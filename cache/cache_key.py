"""Cache key types for archived responses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CacheKey:
    original_url: str
    timestamp: str
    modifier: str
