"""Wayback fetching and redirect handling."""

from __future__ import annotations

import logging
from typing import Optional

import requests

from cache import CacheKey, CacheStore, CachedResponse, NoOpCacheStore

from .wayback_url import (
    build_wayback_url,
    detect_wayback_modifier,
    ensure_archive_modifier,
)


logger = logging.getLogger(__name__)


class WaybackFetchError(Exception):
    """Raised when the proxy cannot fetch an archived response."""


class WaybackClient:
    """Small wrapper around requests for archive fetches."""

    def __init__(
        self,
        session: requests.Session,
        cache_store: Optional[CacheStore] = None,
        timeout: int = 15,
        max_redirects: int = 5,
    ) -> None:
        self.session = session
        self.cache_store = cache_store or NoOpCacheStore()
        self.timeout = timeout
        self.max_redirects = max_redirects

    def fetch(self, original_url: str, timestamp: str) -> CachedResponse:
        modifier = detect_wayback_modifier(original_url)
        key = CacheKey(
            original_url=original_url,
            timestamp=str(timestamp),
            modifier=modifier,
        )

        cached = self.cache_store.get(key)
        if cached is not None:
            return cached

        fetch_url = build_wayback_url(original_url, str(timestamp), modifier)
        response = self._fetch_with_redirects(fetch_url, modifier)
        cached_response = CachedResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,
            reason=response.reason or "OK",
        )
        self.cache_store.set(key, cached_response)
        return cached_response

    def _fetch_with_redirects(
        self, fetch_url: str, modifier: str
    ) -> requests.Response:
        last_response: Optional[requests.Response] = None

        try:
            for _ in range(self.max_redirects):
                last_response = self.session.get(
                    fetch_url,
                    stream=False,
                    timeout=self.timeout,
                    allow_redirects=False,
                )
                if (
                    last_response.status_code in [301, 302, 303, 307, 308]
                    and "Location" in last_response.headers
                ):
                    fetch_url = self._next_redirect_url(
                        last_response.headers["Location"], modifier
                    )
                    continue
                return last_response
        except requests.RequestException as exc:
            logger.warning("Wayback fetch failed for %s: %s", fetch_url, exc)
            raise WaybackFetchError(str(exc)) from exc

        if last_response is None:
            raise WaybackFetchError("Wayback did not return a response")
        return last_response

    @staticmethod
    def _next_redirect_url(location: str, modifier: str) -> str:
        if location.startswith("/"):
            location = "https://web.archive.org" + location
        return ensure_archive_modifier(location, modifier)
