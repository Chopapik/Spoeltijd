import socketserver
import requests
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0'
})

adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100)
session.mount('https://', adapter)
session.mount('http://', adapter)

class ProxyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            request_data = self.request.recv(4096)
            if not request_data:
                return

            try:
                first_line = request_data.split(b'\n')[0]
                method, bUrl, _ = first_line.split(b' ')
            except ValueError:
                return

            if method == b'CONNECT':
                return

            parsedUrl = urlparse(bUrl.decode("utf-8"))
            print("client asked for", parsedUrl)

            archiveUrl = "https://web.archive.org/web/2002if_/" + parsedUrl.netloc + parsedUrl.path
            if parsedUrl.query:
                archiveUrl += "?" + parsedUrl.query

            # Deciding on what to fetch and what to stream
            if "im_/" in archiveUrl:
                print("--------------------------------")
                print(f"Fetching image: {parsedUrl.path}")
                print(f"Downloading from: https://web.archive.org{parsedUrl.path}")
                fetch_url = "https://web.archive.org" + parsedUrl.path
                print("--------------------------------")
            else:
                print("--------------------------------")
                print(f"Downloading: {archiveUrl}")
                print("Requesting HTML content...")
                fetch_url = archiveUrl
                print("--------------------------------")

            # Use a single response stream for header + chunked content
            with session.get(fetch_url, stream=True, timeout=10) as response:
                content_type = response.headers.get('Content-Type', 'application/octet-stream')
                content_length = response.headers.get('Content-Length')
                
                headers = [
                    f"HTTP/1.0 {response.status_code} {response.reason}",
                    f"Content-Type: {content_type}",
                    f"Connection: close"
                ]
                if content_length:
                    headers.append(f"Content-Length: {content_length}")
                
                header_str = "\r\n".join(headers) + "\r\n\r\n"
                self.request.sendall(header_str.encode('utf-8'))

                # Stream the content back to the client
                for chunk in response.iter_content(chunk_size=8192):
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
    HOST, PORT = "0.0.0.0", 8080
    print(f"poeltijd bridge starts on port {PORT}...")
    
    with ThreadingTCPServer((HOST, PORT), ProxyHandler) as server:
        server.serve_forever()