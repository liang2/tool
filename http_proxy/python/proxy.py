import http.server
import socketserver
import ssl
import urllib.parse
import http.client
import socket

class ProxyHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_CONNECT(self):
        host, port = self.path.split(':')
        port = int(port) if port else 443

        try:
            self.send_response(200, 'Connection established')
            self.end_headers()
            self.wfile.flush()

            # 建立隧道连接
            with socket.create_connection((host, port)) as tunnel:
                self.connection.setblocking(0)
                tunnel.setblocking(0)
                while True:
                    try:
                        data = self.connection.recv(4096)
                        if not data:
                            break
                        tunnel.sendall(data)
                    except BlockingIOError:
                        pass

                    try:
                        data = tunnel.recv(4096)
                        if not data:
                            break
                        self.connection.sendall(data)
                    except BlockingIOError:
                        pass
        except Exception as e:
            self.send_error(502, f"Bad Gateway: {e}")

    def do_METHOD(self):
        target_url = self.path[1:]
        parsed_url = urllib.parse.urlparse(target_url)

        context = ssl._create_unverified_context()
        conn = http.client.HTTPSConnection(parsed_url.netloc, context=context)

        try:
            headers = {key: value for key, value in self.headers.items()}
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None

            conn.request(self.command, parsed_url.path + ('?' + parsed_url.query if parsed_url.query else ''), body, headers)
            response = conn.getresponse()

            self.send_response(response.status)
            for header, value in response.getheaders():
                self.send_header(header, value)
            self.end_headers()

            while chunk := response.read(4096):
                self.wfile.write(chunk)
        except Exception as e:
            self.send_error(502, f"Bad Gateway: {e}")
        finally:
            conn.close()

    do_GET = do_METHOD
    do_POST = do_METHOD
    do_PUT = do_METHOD
    do_DELETE = do_METHOD
    do_HEAD = do_METHOD
    do_OPTIONS = do_METHOD
    do_PATCH = do_METHOD

PORT = 80
with socketserver.TCPServer(("", PORT), ProxyHTTPRequestHandler) as httpd:
    print(f"Serving on port {PORT}")
    httpd.serve_forever()