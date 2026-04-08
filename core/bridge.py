"""Spoeltijd bridge: HTTP session and proxy server startup."""

import threading
import requests
from requests.adapters import HTTPAdapter

from .constants import PORT
from network.proxy_handler import ProxyHandler, ThreadingTCPServer


class Bridge:
    """Bridge state (current year) and HTTP session to Wayback; starts the proxy server."""

    def __init__(self, year: int, month: int = None, day: int = None):
        self.current_year = year
        self.current_month = month
        self.current_day = day
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=200, pool_maxsize=200)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    @property
    def current_timestamp(self) -> str:
        if not self.current_month:
            return f"{self.current_year}"
        if not self.current_day:
            return f"{self.current_year}{int(self.current_month):02d}"
        return f"{self.current_year}{int(self.current_month):02d}{int(self.current_day):02d}"

    def start_server(self, port: int = PORT):
        print(f"--- Spoeltijd Bridge running on port {port} ---")
        print("--- Waiting for connections... ---")

        def run_server():
            with ThreadingTCPServer(("0.0.0.0", port), ProxyHandler) as server:
                server.bridge = self
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    print("\nShutting down Spoeltijd Bridge...")

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
