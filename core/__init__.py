"""Core orchestration and shared constants."""

from .app_state import AppState
from .constants import PORT

__all__ = ["AppState", "Bridge", "PORT"]


def __getattr__(name):
    if name == "Bridge":
        from .bridge import Bridge

        return Bridge
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
