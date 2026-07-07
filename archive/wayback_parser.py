"""Backward-compatible wrapper around Wayback URL helpers."""

from __future__ import annotations

import datetime
from urllib.parse import urlparse

from .wayback_url import build_wayback_url


def get_archive_url(raw_url_bytes, target_year):
    """
    Return the Wayback URL for a browser request.

    Older code imported this function directly, so it remains as a thin wrapper
    while the reusable logic lives in archive.wayback_url.
    """
    if target_year is None:
        target_timestamp = str(datetime.datetime.now().year)
    else:
        target_timestamp = str(target_year)

    if isinstance(raw_url_bytes, bytes):
        url_str = raw_url_bytes.decode("utf-8", errors="ignore")
    else:
        url_str = raw_url_bytes

    return build_wayback_url(url_str, target_timestamp), urlparse(url_str)
