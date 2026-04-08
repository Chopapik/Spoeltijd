"""Archive layer: Wayback URL parsing and HTML rewrite/injection."""

from .wayback_parser import get_archive_url
from .html_injector import inject_wayback_tags

__all__ = ["get_archive_url", "inject_wayback_tags"]
