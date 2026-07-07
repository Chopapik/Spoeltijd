"""HTTP proxy handler and multithreaded TCP server for Spoeltijd."""

from __future__ import annotations

import logging
import socketserver

from .request_parser import RequestParseError, parse_http_request
from .response_writer import ResponseWriter
from .routes import Router


logger = logging.getLogger(__name__)


class ProxyHandler(socketserver.BaseRequestHandler):
    """Receives one browser request and delegates parsing/routing."""

    def handle(self) -> None:
        try:
            request_data = self.request.recv(16384)
            if not request_data:
                return

            try:
                parsed_request = parse_http_request(request_data)
            except RequestParseError as exc:
                logger.debug("Ignoring malformed request: %s", exc)
                return

            writer = ResponseWriter(self.request)
            Router(self.server.bridge).dispatch(parsed_request, writer)
        except Exception:
            logger.exception("Unexpected proxy handler error")
            try:
                ResponseWriter(self.request).send_error(502, "Proxy request failed.")
            except OSError:
                logger.debug("Could not send proxy error response", exc_info=True)
        finally:
            self.request.close()


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
