import socketserver
import requests
import re
import json
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from wayback_parser import get_archive_url
import threading
import datetime
PORT = 8080

class Bridge:
    def __init__(self, year):
        self.current_year = year
        self.session = requests.Session()
        self.adapter = HTTPAdapter(pool_connections=200, pool_maxsize=200)
        self.session.mount("https://", self.adapter)
        self.session.mount("http://", self.adapter)

    import threading

    def start_server(self, port: int = 8080):
        print(f"--- Spoeltijd Bridge running on port {port} ---")
        print(f"--- Waiting for connections... ---")

        def run_server():
            with self.ThreadingTCPServer(("0.0.0.0", port), self.ProxyHandler) as server:
                server.bridge = self
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    print("\nShutting down Spoeltijd Bridge...")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

    # Rewrite src/href in HTML so assets load via Wayback (im_/js_/cs_ prefixes)
    def inject_wayback_tags(self, html_bytes, base_url, year: str | None = None):
        if year is None:
            year = str(self.current_year)

        try:
            html_str = html_bytes.decode("utf-8", errors="ignore")
            pattern = r'(src|href)=([\"\'])(.*?)([\"\'])'

            def replacer(match):
                attr_name = match.group(1)
                quote = match.group(2)
                url = match.group(3)

                if (
                    not url
                    or url.startswith("#")
                    or url.lower().startswith("javascript:")
                    or "web.archive.org" in url
                ):
                    return match.group(0)

                clean_ext = url.split("?")[0].split(".")[-1].lower()
                if clean_ext in ["jpg", "jpeg", "gif", "png", "bmp", "ico", "tif", "tiff"]:
                    mod = "im_"
                elif clean_ext in ["js"]:
                    mod = "js_"
                elif clean_ext in ["css"]:
                    mod = "cs_"
                else:
                    return match.group(0)

                absolute_url = urljoin(base_url, url)
                if not absolute_url.startswith("http"):
                    return match.group(0)

                new_url = f"/web/{year}{mod}/{absolute_url}"
                return f"{attr_name}={quote}{new_url}{quote}"

            patched_html = re.sub(pattern, replacer, html_str, flags=re.IGNORECASE)
            year_script = (
                f'<div id="spoeltijd-meta" data-year="{self.current_year}" style="display:none"></div>'
                '<script>(function(){'
                'var m=document.getElementById("spoeltijd-meta");'
                'if(!m)return;'
                'var initialYear=parseInt(m.getAttribute("data-year"),10);'
                'function check(){'
                'fetch("/spoeltijd/year").then(function(r){return r.json();}).then(function(d){'
                'if(d.year!==initialYear)location.reload();'
                '}).catch(function(){});'
                '}'
                'setInterval(check,1500);'
                '})();</script>'
            )
            footer = (
                f'<div style="position:fixed;bottom:0;left:0;right:0;background:#000;color:#fff;'
                f'font-family:Times New Roman,Times,serif;font-size:10px;padding:2px;text-align:center;">'
                f'* SPOELTIJD * | {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                f'</div>'
            )
            if re.search(r"</body>", patched_html, re.IGNORECASE):
                patched_html = re.sub(
                    r"(</body>)", year_script + footer + r"\1", patched_html, count=1, flags=re.IGNORECASE
                )
            else:
                patched_html = patched_html + year_script + footer
            return patched_html.encode("utf-8")

        except Exception as e:
            print(f"[!] Regex rewrite error: {e}")
            return html_bytes

    class ProxyHandler(socketserver.BaseRequestHandler):
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

                # Access the owning Bridge instance via the server
                bridge = self.server.bridge

                # Endpoint: aktualny rok z bridge (encoder) – przeglądarka odświeża stronę przy zmianie
                path = urlparse(full_url).path if full_url.startswith("http") else full_url.split("?")[0]
                if path.rstrip("/") == "/spoeltijd/year":
                    body = json.dumps({"year": bridge.current_year}).encode("utf-8")
                    response = (
                        b"HTTP/1.0 200 OK\r\n"
                        b"Content-Type: application/json; charset=utf-8\r\n"
                        b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                        b"Connection: close\r\n\r\n" + body
                    )
                    self.request.sendall(response)
                    return

                fetch_url, parsed_url_obj = get_archive_url(
                    full_url, target_year=str(bridge.current_year)
                )
                r = bridge.session.get(
                    fetch_url, stream=True, timeout=15, allow_redirects=True
                )

                content_type = r.headers.get("Content-Type", "").lower()
                is_html = "text/html" in content_type

                # HTML: rewrite asset URLs and send; other types: stream as-is
                if is_html:
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
                self.request.close()

    class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        daemon_threads = True
