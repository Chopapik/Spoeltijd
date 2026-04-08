"""HTTP proxy handler and multithreaded TCP server for Spoeltijd."""

import socketserver
import datetime
import json
import os
import re
from urllib.parse import urlparse, parse_qs

from archive.wayback_parser import get_archive_url
from archive.html_injector import inject_wayback_tags
from core.constants import GIF_1X1, GIF_2X2


class ProxyHandler(socketserver.BaseRequestHandler):
    """Handles proxy requests: pixel/year endpoints, Wayback forwarding, HTML injection."""

    def handle(self):
        try:
            request_data = self.request.recv(16384)
            if not request_data:
                return

            try:
                # Separate headers from the request body
                header_block = request_data.split(b"\r\n\r\n")[0].decode("utf-8", errors="ignore")
                lines = header_block.split("\r\n")
                line = lines[0]
                method, full_url, _ = line.split(" ")
                host_header = ""
                for h in lines[1:]:
                    if h.lower().startswith("host:"):
                        host_header = h.split(":", 1)[1].strip()
                        break

                # >>>Handle Transparent Proxy <<<
                if not full_url.startswith("http"):
                    full_url = f"http://{host_header}{full_url}"
                # >>> END Handle Transparent Proxy <<<

            except Exception:
                return

            if method == "CONNECT":
                return

            bridge = self.server.bridge
            parsed = urlparse(full_url)
            path = parsed.path if full_url.startswith("http") else full_url.split("?")[0]
            query_params = parse_qs(parsed.query)
            parsed_host = parsed.netloc.split(":", 1)[0].lower()
            header_host = host_header.split(":", 1)[0].lower()
            is_config_host = parsed_host == "spoeltijd.config" or header_host == "spoeltijd.config"

            # Config host endpoints
            if is_config_host and path.rstrip("/") == "":
                self._handle_config_page()
                return
            if is_config_host and path.rstrip("/") == "/year":
                self._handle_year(bridge)
                return
            if is_config_host and path.rstrip("/") == "/save":
                self._handle_save_config(bridge, query_params)
                return

            # Endpoint: stealth pixel – browser checks if year changed
            if path.rstrip("/") == "/spoeltijd/pixel":
                self._handle_pixel(bridge, query_params)
                return

            # Endpoint: current year (JSON)
            if path.rstrip("/") == "/spoeltijd/year":
                self._handle_year(bridge)
                return

            # Fallback config endpoints by path
            if path.rstrip("/") == "/spoeltijd/config":
                self._handle_config_page()
                return
            if path.rstrip("/") == "/spoeltijd/config/save":
                self._handle_save_config(bridge, query_params)
                return

            # Standard Wayback proxy
            self._handle_wayback_proxy(bridge, full_url, parsed)

        except Exception:
            pass
        finally:
            self.request.close()

    def _handle_pixel(self, bridge, query_params):
        client_timestamp = ""
        y_values = query_params.get("y", [])
        if y_values:
            try:
                client_timestamp = str(int(y_values[0]))
            except (ValueError, IndexError):
                client_timestamp = ""
        if not client_timestamp:
            t_values = query_params.get("t", [])
            if t_values:
                client_timestamp = str(t_values[0]).strip()

        if bridge.current_timestamp == client_timestamp:
            img_data = GIF_1X1
        else:
            print(
                f"[{datetime.datetime.now().time()}] Signal -> Reload triggered (Target: {bridge.current_timestamp})"
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
        body = json.dumps(
            {
                "year": bridge.current_year,
                "month": bridge.current_month,
                "day": bridge.current_day,
                "timestamp": bridge.current_timestamp,
            }
        ).encode("utf-8")
        response = (
            b"HTTP/1.0 200 OK\r\n"
            b"Content-Type: application/json; charset=utf-8\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + body
        )
        self.request.sendall(response)

    def _handle_config_page(self):
        config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "ui",
        "config.html",
    )
        try:
            with open(config_path, "rb") as f:
                body = f.read()
            status = b"HTTP/1.0 200 OK\r\n"
        except Exception:
            body = b"<html><body><h1>config.html not found</h1></body></html>"
            status = b"HTTP/1.0 404 Not Found\r\n"

        response = (
            status
            + b"Content-Type: text/html; charset=utf-8\r\n"
            + b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            + b"Connection: close\r\n\r\n" + body
        )
        self.request.sendall(response)

    def _handle_save_config(self, bridge, query_params):
        year = bridge.current_year
        month = bridge.current_month
        day = bridge.current_day

        year_values = query_params.get("year", [])
        if year_values:
            try:
                year = int(year_values[0])
            except (ValueError, IndexError):
                year = bridge.current_year

        month_values = query_params.get("month", [])
        raw_month = month_values[0].strip() if month_values else ""
        if raw_month == "":
            month = None
        else:
            try:
                month_candidate = int(raw_month)
                month = month_candidate if 1 <= month_candidate <= 12 else None
            except ValueError:
                month = None

        day_values = query_params.get("day", [])
        raw_day = day_values[0].strip() if day_values else ""
        if raw_day == "":
            day = None
        else:
            try:
                day_candidate = int(raw_day)
                day = day_candidate if 1 <= day_candidate <= 31 else None
            except ValueError:
                day = None

        if month is None:
            day = None

        bridge.current_year = year
        bridge.current_month = month
        bridge.current_day = day

        response = (
            b"HTTP/1.0 302 Found\r\n"
            b"Location: http://spoeltijd.config/\r\n"
            b"Connection: close\r\n\r\n"
        )
        self.request.sendall(response)

    def _handle_wayback_proxy(self, bridge, full_url, parsed):
        fetch_url, _ = get_archive_url(
            full_url, target_year=bridge.current_timestamp
        )

        # Restore original URL modifier (for example: id_, im_)
        mod_match = re.search(r'/web/\d{4,14}([a-z]{2}_)/', fetch_url)
        modifier = mod_match.group(1) if mod_match else "id_"

        try:
            # Manual redirect loop: force Wayback to keep raw source mode (id_)
            for _ in range(5):
                r = bridge.session.get(
                    fetch_url, stream=True, timeout=15, allow_redirects=False
                )
                if r.status_code in [301, 302, 303, 307, 308] and 'Location' in r.headers:
                    next_url = r.headers['Location']
                    if next_url.startswith('/'):
                        next_url = "https://web.archive.org" + next_url
                    
                    # Regex finds 4..14 digits and appends modifier only if it is missing
                    if not re.search(r'/web/\d{4,14}[a-z]{2}_/', next_url):
                        next_url = re.sub(
                            r'(/web/\d{4,14})/',
                            r'\g<1>' + modifier + '/',
                            next_url,
                            count=1,
                        )
                    fetch_url = next_url
                else:
                    break

        except Exception as e:
            print(f"Wayback error: {e}")
            return

        content_type = r.headers.get("Content-Type", "").lower()
        is_html = "text/html" in content_type

        if is_html:
            modified_body = inject_wayback_tags(
                r.content,
                base_url=full_url,
                year=bridge.current_timestamp,
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