"""Spoeltijd bridge: HTTP session and proxy server startup."""

import threading
import requests
from requests.adapters import HTTPAdapter

from .constants import PORT
from .proxy_handler import ProxyHandler, ThreadingTCPServer


class Bridge:
    """Bridge state (current year) and HTTP session to Wayback; starts the proxy server."""

    def __init__(self, year: int):
        self.current_year = year
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=200, pool_maxsize=200)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

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
