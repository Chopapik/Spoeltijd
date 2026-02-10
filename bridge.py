from socket import socket, AF_INET, SOCK_STREAM,SOL_SOCKET, SO_REUSEADDR
from urllib.parse import urlparse
from urllib.request import urlopen, Request
import threading

server_socket = socket(AF_INET, SOCK_STREAM)


server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
server_socket.bind(('0.0.0.0', 8080))
server_socket.listen(10)

def handleClient(client_socket, client_address):
    try:
        print(f"Connected by {client_address}")
        request_data = client_socket.recv(1024)
        if not request_data:
            client_socket.close()
            return

        try:
            bUrl = request_data.split(b" ")[1]
        except IndexError:
            client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\n\r\nBad Request")
            client_socket.close()
            return



        parsedUrl = urlparse(bUrl.decode("utf-8"))
        archiveUrl = "http://web.archive.org/web/2002id_/" + parsedUrl.netloc + parsedUrl.path
        if parsedUrl.query:
            archiveUrl += "?" + parsedUrl.query

        req = Request(archiveUrl, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0'})
        response = urlopen(req)
        content_type = response.info().get('Content-Type')

        headers = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nConnection: close\r\n\r\n"
        client_socket.sendall(headers.encode('utf-8'))

        while True:
            chunk = response.read(4096)
            if not chunk:
                break
            client_socket.sendall(chunk)

    except Exception as e:
        print(f"Error handling request from {client_address}: {e}")
        try:
            client_socket.sendall(b"HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nInternal Server Error")
        except Exception:
            pass
    finally:
        client_socket.close()


while True:
    client_socket, client_address = server_socket.accept()
    threading.Thread(target=handleClient, args=(client_socket, client_address)).start()