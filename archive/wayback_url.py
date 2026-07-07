"""Small helpers for building Wayback Machine URLs."""

from __future__ import annotations

import os
import re
from typing import Optional
from urllib.parse import urlparse


IMAGE_EXTENSIONS = {".gif", ".jpg", ".jpeg", ".png", ".bmp", ".ico"}
CSS_EXTENSIONS = {".css"}
JS_EXTENSIONS = {".js"}
OBJECT_EXTENSIONS = {".swf", ".class", ".cab", ".dcr"}
DEFAULT_MODIFIER = "id_"


def detect_wayback_modifier(url_or_path: str) -> str:
    """Return the Wayback modifier that best matches a URL or path."""
    archive_match = re.search(r"/web/\d{4,14}([a-z]{2}_)/", url_or_path)
    if archive_match:
        return archive_match.group(1)

    parsed = urlparse(url_or_path)
    path = parsed.path.lower() if parsed.path else str(url_or_path).lower()
    _, extension = os.path.splitext(path)

    if extension in IMAGE_EXTENSIONS:
        return "im_"
    if extension in CSS_EXTENSIONS:
        return "cs_"
    if extension in JS_EXTENSIONS:
        return "js_"
    if extension in OBJECT_EXTENSIONS:
        return "oe_"
    return DEFAULT_MODIFIER


def build_wayback_url(
    original_url: str, timestamp: str, modifier: Optional[str] = None
) -> str:
    """
    Build the archive URL used by the proxy.

    Existing /web/... paths are pass-through links from injected HTML and are
    sent directly to web.archive.org, preserving the old proxy behavior.
    """
    parsed = urlparse(original_url)
    query = f"?{parsed.query}" if parsed.query else ""

    if parsed.path.startswith("/web/"):
        return f"https://web.archive.org{parsed.path}{query}"

    selected_modifier = modifier or detect_wayback_modifier(original_url)
    return (
        f"https://web.archive.org/web/{timestamp}{selected_modifier}/"
        f"{parsed.netloc}{parsed.path}{query}"
    )


def ensure_archive_modifier(url: str, modifier: str) -> str:
    """Add a Wayback modifier to a redirect URL if Wayback omitted it."""
    if re.search(r"/web/\d{4,14}[a-z]{2}_/", url):
        return url
    return re.sub(r"(/web/\d{4,14})/", r"\g<1>" + modifier + "/", url, count=1)
