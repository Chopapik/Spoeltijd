"""Shared Spoeltijd date state."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Optional, Tuple


_UNSET = object()


@dataclass
class AppState:
    """Thread-safe enough shared date state for the proxy and hardware panel."""

    current_year: int
    current_month: Optional[int] = None
    current_day: Optional[int] = None
    _lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, repr=False, compare=False
    )

    @property
    def timestamp(self) -> str:
        year, month, day = self.snapshot()
        if not month:
            return f"{year}"
        if not day:
            return f"{year}{int(month):02d}"
        return f"{year}{int(month):02d}{int(day):02d}"

    def snapshot(self) -> Tuple[int, Optional[int], Optional[int]]:
        with self._lock:
            return self.current_year, self.current_month, self.current_day

    def update(
        self,
        year: Any = _UNSET,
        month: Any = _UNSET,
        day: Any = _UNSET,
    ) -> None:
        """Update one or more date parts under one lock."""
        with self._lock:
            if year is not _UNSET:
                self.current_year = int(year)
            if month is not _UNSET:
                self.current_month = month
                if month is None:
                    self.current_day = None
            if day is not _UNSET:
                self.current_day = day
