"""Direct-first asset fetching with Wayback fallback."""

from __future__ import annotations

import logging
from typing import Iterable, Optional

import requests

from cache import CachedResponse

from .asset_url import clean_http_asset_url
from .wayback_client import WaybackClient


logger = logging.getLogger(__name__)


class AssetClient:
    """Fetch page assets directly over HTTP before falling back to Wayback."""

    def __init__(
        self,
        session: requests.Session,
        wayback_client: WaybackClient,
        timeout: int = 5,
        miss_statuses: Optional[Iterable[int]] = None,
    ) -> None:
        self.session = session
        self.wayback_client = wayback_client
        self.timeout = timeout
        self.miss_statuses = set(miss_statuses or {403, 404})

    def fetch(self, original_url: str, timestamp: str) -> CachedResponse:
        direct_url = clean_http_asset_url(original_url)
        logger.info("ASSET direct TRY %s", direct_url)

        try:
            direct_response = self.session.get(
                direct_url,
                stream=False,
                timeout=self.timeout,
                allow_redirects=True,
            )
            if self._is_direct_hit(direct_response):
                logger.info("ASSET direct HIT %s", direct_url)
                return CachedResponse(
                    status_code=direct_response.status_code,
                    headers=dict(direct_response.headers),
                    content=direct_response.content,
                    reason=direct_response.reason or "OK",
                )

            logger.info(
                "ASSET direct MISS %s status=%s bytes=%s",
                direct_url,
                direct_response.status_code,
                len(direct_response.content or b""),
            )
        except (
            requests.ConnectionError,
            requests.Timeout,
            requests.TooManyRedirects,
        ) as exc:
            logger.info("ASSET direct MISS %s error=%s", direct_url, exc)
        except requests.RequestException as exc:
            logger.info("ASSET direct MISS %s error=%s", direct_url, exc)

        logger.info("ASSET Wayback fallback TRY %s", original_url)
        fallback_response = self.wayback_client.fetch(original_url, timestamp)
        logger.info("ASSET Wayback fallback HIT %s", original_url)
        return fallback_response

    def _is_direct_hit(self, response: requests.Response) -> bool:
        if response.status_code < 200 or response.status_code >= 400:
            return False
        if not response.content:
            return False
        return True
