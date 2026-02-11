import socketserver
import requests
from requests.adapters import HTTPAdapter
from wayback_parser import get_archive_url

PORT = 8080

# One shared session with a large connection pool for faster repeated requests.
session = requests.Session()
adapter = HTTPAdapter(pool_connections=200, pool_maxsize=200)
session.mount('https://', adapter)
session.mount('http://', adapter)


class ProxyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            # Read the raw HTTP request from the client (up to 16 KB).
            request_data = self.request.recv(16384)
            if not request_data:
                return

            # Parse the first line to get method (GET, etc.) and the full URL.
            try:
                line = request_data.split(b'\n')[0].decode('utf-8', errors='ignore').strip()
                method, full_url, _ = line.split(' ')
            except Exception:
                return

            # Ignore CONNECT (e.g. HTTPS tunnel); we only handle GET.
            if method == 'CONNECT':
                return

            # Turn the requested URL into the correct Wayback Machine archive URL.
            fetch_url = get_archive_url(full_url, target_year="2002")[0]

            # Fetch the resource from the archive; stream so we can pipe large responses.
            r = session.get(fetch_url, stream=True, timeout=15, allow_redirects=True)
            content_type = r.headers.get('Content-Type', 'text/html')

            # Send headers, then stream the body in chunks (works for all content types).
            content_length = r.headers.get('Content-Length')
            headers_list = [
                f"HTTP/1.0 {r.status_code} OK",
                f"Content-Type: {content_type}",
                "Connection: close",
            ]
            if content_length is not None:
                headers_list.insert(2, f"Content-Length: {content_length}")
            headers_list.append("\r\n")
            self.request.sendall("\r\n".join(headers_list).encode('utf-8'))
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


if __name__ == "__main__":
    print(f"--- Spoeltijd bridge starts on port {PORT} ---")
    with ThreadingTCPServer(("0.0.0.0", PORT), ProxyHandler) as server:
        server.serve_forever()