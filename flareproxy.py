import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

# Get FlareSolverr URL from environment variable or use default
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "http://flaresolverr:8191/v1")


class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):
    def handle_request(self):
        """Handle the core logic for GET and CONNECT requests."""
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

    def do_GET(self):
        """Handle GET requests."""
        self.handle_request()

    def do_CONNECT(self):
        """Handle CONNECT requests."""
        self.handle_request()


if __name__ == "__main__":
    server_address = ("", 8080)
    httpd = HTTPServer(server_address, ProxyHTTPRequestHandler)
    print("FlareProxy adapter running on port 8080")
    httpd.serve_forever()
