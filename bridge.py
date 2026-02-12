import socketserver
import requests
import re
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from wayback_parser import get_archive_url

PORT = 8080

# One shared session with a large connection pool for faster repeated requests.
session = requests.Session()
adapter = HTTPAdapter(pool_connections=200, pool_maxsize=200)
session.mount('https://', adapter)
session.mount('http://', adapter)

# Rewrite src/href in HTML so assets load via Wayback (im_/js_/cs_ prefixes)
def inject_wayback_tags(html_bytes, base_url, year="2002"):
    try:
        html_str = html_bytes.decode('utf-8', errors='ignore')
        pattern = r'(src|href)=([\"\'])(.*?)([\"\'])'

        def replacer(match):
            attr_name = match.group(1)
            quote = match.group(2)
            url = match.group(3)

            if not url or url.startswith('#') or url.lower().startswith('javascript:') or "web.archive.org" in url:
                return match.group(0)

            clean_ext = url.split('?')[0].split('.')[-1].lower()
            if clean_ext in ['jpg', 'jpeg', 'gif', 'png', 'bmp', 'ico', 'tif', 'tiff']:
                mod = "im_"
            elif clean_ext in ['js']:
                mod = "js_"
            elif clean_ext in ['css']:
                mod = "cs_"
            else:
                return match.group(0)

            absolute_url = urljoin(base_url, url)
            if not absolute_url.startswith('http'):
                return match.group(0)

            new_url = f"/web/{year}{mod}/{absolute_url}"
            return f'{attr_name}={quote}{new_url}{quote}'

        patched_html = re.sub(pattern, replacer, html_str, flags=re.IGNORECASE)
        return patched_html.encode('utf-8')

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
                line = request_data.split(b'\n')[0].decode('utf-8', errors='ignore').strip()
                method, full_url, _ = line.split(' ')
            except Exception:
                return

            if method == 'CONNECT':
                return

            fetch_url, parsed_url_obj = get_archive_url(full_url, target_year="2002")
            r = session.get(fetch_url, stream=True, timeout=15, allow_redirects=True)

            content_type = r.headers.get('Content-Type', '').lower()
            is_html = 'text/html' in content_type

            # HTML: rewrite asset URLs and send; other types: stream as-is
            if is_html:
                body_content = r.content
                modified_body = inject_wayback_tags(body_content, base_url=full_url, year="2002")
                headers_list = [
                    f"HTTP/1.0 {r.status_code} OK",
                    f"Content-Type: {r.headers.get('Content-Type', 'text/html')}",
                    f"Content-Length: {len(modified_body)}",
                    "Connection: close"
                ]
                response_data = "\r\n".join(headers_list).encode('utf-8') + b"\r\n\r\n" + modified_body
                self.request.sendall(response_data)

            else:
                headers_list = [
                    f"HTTP/1.0 {r.status_code} OK",
                    f"Content-Type: {r.headers.get('Content-Type', 'application/octet-stream')}",
                    "Connection: close"
                ]
                if r.headers.get('Content-Length'):
                    headers_list.append(f"Content-Length: {r.headers.get('Content-Length')}")
                self.request.sendall("\r\n".join(headers_list).encode('utf-8') + b"\r\n\r\n")
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        self.request.sendall(chunk)

        except Exception as e:
            pass
        finally:
            self.request.close()


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    print(f"--- Hexoo Bridge (Socket Mode + Turbo Rewrite) running on port {PORT} ---")
    print(f"--- Waiting for connections... ---")
    with ThreadingTCPServer(("0.0.0.0", PORT), ProxyHandler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down Hexoo Bridge...")
