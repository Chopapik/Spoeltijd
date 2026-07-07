"""Spoeltijd bridge: HTTP session, shared state, and proxy server startup."""

import logging
import threading
from typing import Optional

import requests
from requests.adapters import HTTPAdapter

from archive.wayback_client import WaybackClient
from cache import CacheStore, NoOpCacheStore

from .constants import PORT
from .app_state import AppState
from network.proxy_handler import ProxyHandler, ThreadingTCPServer


logger = logging.getLogger(__name__)


class Bridge:
    """Bridge state and HTTP session to Wayback; starts the proxy server."""

    def __init__(
        self,
        year: int = 2002,
        month: Optional[int] = None,
        day: Optional[int] = None,
        state: Optional[AppState] = None,
        cache_store: Optional[CacheStore] = None,
    ):
        self.state = state or AppState(year, month, day)
        self.cache_store = cache_store or NoOpCacheStore()
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=200, pool_maxsize=200)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.wayback_client = WaybackClient(self.session, self.cache_store)

    @property
    def current_year(self) -> int:
        return self.state.snapshot()[0]

    @current_year.setter
    def current_year(self, value: int) -> None:
        self.state.update(year=value)

    @property
    def current_month(self) -> Optional[int]:
        return self.state.snapshot()[1]

    @current_month.setter
    def current_month(self, value: Optional[int]) -> None:
        self.state.update(month=value)

    @property
    def current_day(self) -> Optional[int]:
        return self.state.snapshot()[2]

    @current_day.setter
    def current_day(self, value: Optional[int]) -> None:
        self.state.update(day=value)

    @property
    def current_timestamp(self) -> str:
        return self.state.timestamp

    def serve_forever(self, port: int = PORT) -> None:
        logger.info("Spoeltijd Bridge running on port %s", port)
        logger.info("Waiting for connections...")

        with ThreadingTCPServer(("0.0.0.0", port), ProxyHandler) as server:
            server.bridge = self
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                logger.info("Shutting down Spoeltijd Bridge...")

    def start_server(self, port: int = PORT) -> threading.Thread:
        thread = threading.Thread(target=self.serve_forever, args=(port,), daemon=True)
        thread.start()
        return thread
