import socketserver
import requests
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter


session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0'
})

adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)
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

            if "web.archive.org" in parsedUrl.netloc:
                archiveUrl = bUrl.decode("utf-8")
            else:
                archiveUrl = "https://web.archive.org/web/2002if_/" + parsedUrl.netloc + parsedUrl.path
                if parsedUrl.query:
                    archiveUrl += "?" + parsedUrl.query

            print(f"Downloading: {parsedUrl.netloc}{parsedUrl.path}")

            response = session.get(archiveUrl, stream=True, timeout=10)


            headers = f"HTTP/1.1 200 OK\r\nContent-Type: {response.headers.get('Content-Type')}\r\nConnection: close\r\n\r\n"
            self.request.sendall(headers.encode('utf-8'))

            for chunk in response.iter_content(chunk_size=4096):
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