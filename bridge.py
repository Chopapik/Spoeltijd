import socketserver
import requests
import re
import json
import threading
import datetime
import time
import random
from urllib.parse import urljoin, urlparse, parse_qs
from requests.adapters import HTTPAdapter
from wayback_parser import get_archive_url

PORT = 8080

# Binary data for 1x1 and 2x2 GIFs. Used for the stealth pixel endpoint.
GIF_1X1 = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
GIF_2X2 = b'\x47\x49\x46\x38\x39\x61\x02\x00\x02\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x2c\x00\x00\x00\x00\x02\x00\x02\x00\x00\x02\x02\x84\x51\x00\x3b'

class Bridge:
    def __init__(self, year):
        # Holds the current spoofed year (int)
        self.current_year = year
        # HTTP session with pooling for faster asset proxying
        self.session = requests.Session()
        self.adapter = HTTPAdapter(pool_connections=200, pool_maxsize=200)
        self.session.mount("https://", self.adapter)
        self.session.mount("http://", self.adapter)

    def start_server(self, port: int = 8080):
        print(f"--- Spoeltijd Bridge running on port {port} ---")
        print(f"--- Waiting for connections... ---")

        def run_server():
            # Start a multi-threaded TCP server for the proxy.
            with self.ThreadingTCPServer(("0.0.0.0", port), self.ProxyHandler) as server:
                # Access the owning Bridge instance via the server
                server.bridge = self
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    print("\nShutting down Spoeltijd Bridge...")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

    def inject_wayback_tags(self, html_bytes, base_url, year: str | None = None):
        """
        Rewrite src/href in HTML so assets load via Wayback (im_/js_/cs_ prefixes)
        Add stealth reload script and footer.
        """
        if year is None:
            year = str(self.current_year)

        try:
            html_str = html_bytes.decode("utf-8", errors="ignore")
            
            # Rewrite HTML src/href so assets point to our local Wayback handler.
            # Only rewrite image, js, css extensions.
            pattern = r'(src|href)=([\"\'])(.*?)([\"\'])'

            def replacer(match):
                attr_name = match.group(1)
                quote = match.group(2)
                url = match.group(3)

                if (not url or url.startswith("#") or 
                    url.lower().startswith("javascript:") or 
                    "web.archive.org" in url):
                    # Do not rewrite external or javascript or hash links.
                    return match.group(0)

                clean_ext = url.split("?")[0].split(".")[-1].lower()
                if clean_ext in ["jpg", "jpeg", "gif", "png", "bmp", "ico", "tif", "tiff"]:
                    mod = "im_"
                elif clean_ext in ["js"]:
                    mod = "js_"
                elif clean_ext in ["css"]:
                    mod = "cs_"
                else:
                    # Not a recognized asset extension, skip rewriting.
                    return match.group(0)

                absolute_url = urljoin(base_url, url)
                if not absolute_url.startswith("http"):
                    # Ignore links that don't resolve to http(s)
                    return match.group(0)

                new_url = f"/web/{year}{mod}/{absolute_url}"
                return f"{attr_name}={quote}{new_url}{quote}"

            patched_html = re.sub(pattern, replacer, html_str, flags=re.IGNORECASE)

            # Remove any legacy meta-refresh tags, since we want our own refresh logic.
            if re.search(r'<meta[^>]*http-equiv=["\']?refresh["\']?[^>]*>', patched_html, re.IGNORECASE):
                patched_html = re.sub(
                    r'<meta[^>]*http-equiv=["\']?refresh["\']?[^>]*>', '', patched_html, flags=re.IGNORECASE)

            # Inject "stealth" monitoring script for checking year in the background and reloading if changed.
            stealth_script = f"""
            <script language="JavaScript">
            <!--
            var spoeltijdYear = {year};
            function spoeltijdPoll() {{
              var img = new Image();
              img.onload = function() {{
                var w = (typeof img.width !== "undefined") ? img.width : 0;
                var h = (typeof img.height !== "undefined") ? img.height : 0;
                // If received 2x2 pixel, year changed – reload page.
                if (w > 1 || h > 1) {{ location.reload(); }}
              }};
              img.src = "/spoeltijd/pixel?y=" + spoeltijdYear + "&t=" + (new Date().getTime());
            }}
            setInterval(spoeltijdPoll, 1500);
            spoeltijdPoll();
            // -->
            </script>
            """

            # Fixed footer with current server time.
            footer = (
                f'<div style="position:fixed;bottom:0;left:0;right:0;background:#fff;color:#000;'
                f'font-family:Times New Roman,Times,serif;font-size:12px;padding:2px;text-align:center;z-index:9999;">'
                f'* SPOELTIJD * | {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                f'</div>'
            )

            injection = footer + stealth_script

            # If there is a </body> tag, place our code right before it. Otherwise, just append.
            if re.search(r"</body>", patched_html, re.IGNORECASE):
                patched_html = re.sub(
                    r"(</body>)", injection + r"\1", patched_html, count=1, flags=re.IGNORECASE
                )
            else:
                patched_html = patched_html + injection

            return patched_html.encode("utf-8")

        except Exception as e:
            print(f"[!] Regex rewrite error: {e}")
            return html_bytes

    class ProxyHandler(socketserver.BaseRequestHandler):
        def handle(self):
            try:
                # Receive the raw HTTP request data
                request_data = self.request.recv(16384)
                if not request_data:
                    return

                try:
                    # Parse the first line of the HTTP request
                    line = (
                        request_data.split(b"\n")[0]
                        .decode("utf-8", errors="ignore")
                        .strip()
                    )
                    method, full_url, _ = line.split(" ")
                except Exception:
                    return

                # We do not support HTTP CONNECT method for HTTPS proxying.
                if method == "CONNECT":
                    return

                # Access the owning Bridge instance via the server
                bridge = self.server.bridge

                # Parse URL and query parameters
                parsed = urlparse(full_url)
                path = parsed.path if full_url.startswith("http") else full_url.split("?")[0]
                query_params = parse_qs(parsed.query)

                # Endpoint: Stealth pixel checker – browser checks here to see if year changed
                if path.rstrip("/") == "/spoeltijd/pixel":
                    try:
                        client_year = int(query_params.get('y', [0])[0])
                    except (ValueError, IndexError):
                        client_year = 0

                    if bridge.current_year == client_year:
                        # Server year matches client – send 1x1 GIF (no reload)
                        img_data = GIF_1X1
                    else:
                        # Year changed – send 2x2 GIF, triggers client reload
                        print(f"[{datetime.datetime.now().time()}] Signal -> Reload triggered (Target: {bridge.current_year})")
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
                    return

                # Endpoint: Get the current spoofed year from Bridge (used by browser for refresh logic)
                if path.rstrip("/") == "/spoeltijd/year":
                    # Return JSON with the current bridge year
                    body = json.dumps({"year": bridge.current_year}).encode("utf-8")
                    response = (
                        b"HTTP/1.0 200 OK\r\n"
                        b"Content-Type: application/json; charset=utf-8\r\n"
                        b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                        b"Connection: close\r\n\r\n" + body
                    )
                    self.request.sendall(response)
                    return

                # # HTML: rewrite asset URLs and send; other types: stream as-is
                # Standard Wayback proxy for all other requests.
                fetch_url, parsed_url_obj = get_archive_url(
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
                    # If content is HTML, rewrite URLs and inject the monitor
                    body_content = r.content
                    modified_body = bridge.inject_wayback_tags(
                        body_content,
                        base_url=full_url,
                        year=str(bridge.current_year),
                    )
                    headers_list = [
                        f"HTTP/1.0 {r.status_code} OK",
                        f"Content-Type: {r.headers.get('Content-Type', 'text/html')}",
                        f"Content-Length: {len(modified_body)}",
                        "Connection: close",
                    ]
                    response_data = (
                        "\r\n".join(headers_list).encode("utf-8")
                        + b"\r\n\r\n"
                        + modified_body
                    )
                    self.request.sendall(response_data)
                else:
                    # For non-HTML: Just relay the data in chunks, as-is.
                    headers_list = [
                        f"HTTP/1.0 {r.status_code} OK",
                        f"Content-Type: {r.headers.get('Content-Type', 'application/octet-stream')}",
                        "Connection: close",
                    ]
                    if r.headers.get("Content-Length"):
                        headers_list.append(
                            f"Content-Length: {r.headers.get('Content-Length')}"
                        )
                    self.request.sendall(
                        "\r\n".join(headers_list).encode("utf-8") + b"\r\n\r\n"
                    )
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            self.request.sendall(chunk)

            except Exception:
                pass
            finally:
                # Always close the socket at the end
                self.request.close()

    class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        daemon_threads = True