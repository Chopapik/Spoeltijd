"""HTTP proxy handler and multithreaded TCP server for Spoeltijd."""

import socketserver
import datetime
import json
from urllib.parse import urlparse, parse_qs

from .wayback_parser import get_archive_url
from .html_injector import inject_wayback_tags
from .constants import GIF_1X1, GIF_2X2


class ProxyHandler(socketserver.BaseRequestHandler):
    """Handles proxy requests: pixel/year endpoints, Wayback forwarding, HTML injection."""

    def handle(self):
        try:
            request_data = self.request.recv(16384)
            if not request_data:
                return

            try:
                line = (
                    request_data.split(b"\n")[0]
                    .decode("utf-8", errors="ignore")
                    .strip()
                )
                method, full_url, _ = line.split(" ")
            except Exception:
                return

            if method == "CONNECT":
                return

            bridge = self.server.bridge
            parsed = urlparse(full_url)
            path = parsed.path if full_url.startswith("http") else full_url.split("?")[0]
            query_params = parse_qs(parsed.query)

            # Endpoint: stealth pixel – browser checks if year changed
            if path.rstrip("/") == "/spoeltijd/pixel":
                self._handle_pixel(bridge, query_params)
                return

            # Endpoint: current year (JSON)
            if path.rstrip("/") == "/spoeltijd/year":
                self._handle_year(bridge)
                return

            # Standard Wayback proxy
            self._handle_wayback_proxy(bridge, full_url, parsed)

        except Exception:
            pass
        finally:
            self.request.close()

    def _handle_pixel(self, bridge, query_params):
        try:
            client_year = int(query_params.get("y", [0])[0])
        except (ValueError, IndexError):
            client_year = 0

        if bridge.current_year == client_year:
            img_data = GIF_1X1
        else:
            print(
                f"[{datetime.datetime.now().time()}] Signal -> Reload triggered (Target: {bridge.current_year})"
            )
            img_data = GIF_2X2

        response = (
            b"HTTP/1.0 200 OK\r\n"
            b"Content-Type: image/gif\r\n"
            b"Cache-Control: no-cache, no-store, must-revalidate\r\n"
            b"Pragma: no-cache\r\n"
            b"Expires: 0\r\n"
            b"Content-Length: " + str(len(img_data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + img_data
        )
        self.request.sendall(response)

    def _handle_year(self, bridge):
        body = json.dumps({"year": bridge.current_year}).encode("utf-8")
        response = (
            b"HTTP/1.0 200 OK\r\n"
            b"Content-Type: application/json; charset=utf-8\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + body
        )
        self.request.sendall(response)

    def _handle_wayback_proxy(self, bridge, full_url, parsed):
        fetch_url, _ = get_archive_url(
            full_url, target_year=str(bridge.current_year)
        )

        try:
            r = bridge.session.get(
                fetch_url, stream=True, timeout=15, allow_redirects=True
            )
        except Exception as e:
            print(f"Wayback error: {e}")
            return

        content_type = r.headers.get("Content-Type", "").lower()
        is_html = "text/html" in content_type

        if is_html:
            modified_body = inject_wayback_tags(
                r.content,
                base_url=full_url,
                year=str(bridge.current_year),
            )
            headers_list = [
                f"HTTP/1.0 {r.status_code} OK",
                f"Content-Type: {r.headers.get('Content-Type', 'text/html')}",
                f"Content-Length: {len(modified_body)}",
                "Connection: close",
            ]
            self.request.sendall(
                "\r\n".join(headers_list).encode("utf-8") + b"\r\n\r\n" + modified_body
            )
        else:
            headers_list = [
                f"HTTP/1.0 {r.status_code} OK",
                f"Content-Type: {r.headers.get('Content-Type', 'application/octet-stream')}",
                "Connection: close",
            ]
            if r.headers.get("Content-Length"):
                headers_list.append(f"Content-Length: {r.headers.get('Content-Length')}")
            self.request.sendall(
                "\r\n".join(headers_list).encode("utf-8") + b"\r\n\r\n"
            )
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    self.request.sendall(chunk)


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
