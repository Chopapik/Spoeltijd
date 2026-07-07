"""Helpers for identifying and normalizing browser asset URLs."""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse, urlunparse


ASSET_EXTENSIONS = {
    ".gif",
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".ico",
    ".webp",
    ".css",
    ".js",
    ".swf",
    ".class",
    ".cab",
    ".dcr",
    ".wav",
    ".mid",
    ".mp3",
}


def is_asset_url(url: str) -> bool:
    """Return True when a URL points at a browser asset by extension."""
    parsed = urlparse(_extract_archived_original_url(url))
    path = parsed.path or url
    _, extension = os.path.splitext(path.lower())
    return extension in ASSET_EXTENSIONS


def clean_http_asset_url(url: str) -> str:
    """Return the direct HTTP form used for first-pass asset fetches."""
    parsed = urlparse(_extract_archived_original_url(url))
    if parsed.scheme in {"http", "https"}:
        parsed = parsed._replace(scheme="http")
    return urlunparse(parsed)


def _extract_archived_original_url(url: str) -> str:
    match = re.search(r"/web/\d{4,14}[a-z]{0,2}_?/(https?://.+)$", url)
    if match:
        return match.group(1)
    return url
