import json
import os
import select
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

# Get FlareSolverr URL from environment variable or use default
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "http://flaresolverr:8191/v1")


class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests."""
        try:
            # Prepare the payload
            headers = {"Content-Type": "application/json"}
            data = {
                "cmd": "request.get",
                "url": self.path.replace("http", "https"),
                "maxTimeout": 60000,
            }

            # Send the POST request to FlareSolverr
            response = requests.post(FLARESOLVERR_URL, headers=headers, json=data)
            json_response = response.json()

            # Forward the response back to the client
            self.send_response(response.status_code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                bytes(json_response.get("solution", {}).get("response", ""), "utf-8")
            )

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_message = json.dumps({"error": str(e)})
            self.wfile.write(error_message.encode("utf-8"))

    def do_CONNECT(self):
        """Handle CONNECT requests by establishing a raw TCP tunnel."""
        try:
            host, _, port = self.path.partition(":")
            port = int(port)
        except (ValueError, AttributeError):
            self.send_error(400, "Bad CONNECT target")
            return

        try:
            remote = socket.create_connection((host, port), timeout=10)
        except (socket.gaierror, socket.error) as e:
            self.send_error(502, f"Cannot connect to {host}:{port}: {e}")
            return

        # Send 200 via raw socket so we don't mix with wfile buffering
        try:
            self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        except socket.error:
            remote.close()
            return

        # Bidirectional relay using select
        socks = [self.request, remote]
        try:
            while True:
                readable, _, exceptional = select.select(socks, [], socks, 30)
                if exceptional or not readable:
                    break
                for s in readable:
                    peer = remote if s is self.request else self.request
                    data = s.recv(8192)
                    if not data:
                        return
                    peer.sendall(data)
        finally:
            remote.close()


if __name__ == "__main__":
    server_address = ("", 8080)
    httpd = ThreadingHTTPServer(server_address, ProxyHTTPRequestHandler)
    print("FlareProxy adapter running on port 8080")
    httpd.serve_forever()
