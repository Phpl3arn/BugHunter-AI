"""Isolated local HTTP laboratory: XSS, SSRF-like and access control."""
import html
import json
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, content, content_type="text/plain"):
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parts = urlsplit(self.path)
        params = parse_qs(parts.query)
        vulnerable = self.server.vulnerable

        if parts.path == "/reflect":
            value = params.get("value", [""])[0][:200]
            output = value if vulnerable else html.escape(value, quote=True)
            self.respond(200, output, "text/html")
            return

        if parts.path == "/admin":
            role = self.headers.get("X-Demo-Role", "guest")
            if role != "admin" and not vulnerable:
                self.respond(403, "Forbidden")
                return
            self.respond(200, "SYNTHETIC_ADMIN_RESOURCE")
            return

        if parts.path == "/internal/metadata":
            self.respond(200, "MOCK_INTERNAL_METADATA")
            return

        if parts.path == "/fetch":
            target = params.get("target", [""])[0]

            # No arbitrary URL or external destination is accepted.
            if target != "internal":
                self.respond(400, "Target not allowed")
                return

            if not vulnerable:
                self.respond(403, "Internal destination blocked")
                return

            # Demonstrate an actual server-side HTTP request,
            # strictly to our own ephemeral loopback test service.
            url = (
                f"http://127.0.0.1:{self.server.server_port}"
                "/internal/metadata"
            )
            with urllib.request.urlopen(url, timeout=2) as response:
                content = response.read(1024).decode("utf-8")

            self.respond(200, content)
            return

        self.respond(404, "Not found")


def make_server(vulnerable, port=0):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.vulnerable = vulnerable
    return server
