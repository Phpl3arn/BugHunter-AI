import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ACCOUNTS = {
    "1": {"id": 1, "owner": "alice", "balance": 120},
    "2": {"id": 2, "owner": "bob", "balance": 250},
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path != "/api/account":
            self.send_error(404)
            return

        user = self.headers.get("X-Demo-User")
        account_id = parse_qs(parsed.query).get("id", [""])[0]

        if user not in ("alice", "bob"):
            self.send_error(401)
            return

        account = ACCOUNTS.get(account_id)

        if account is None:
            self.send_error(404)
            return

        # INTENTIONALLY VULNERABLE:
        # Missing authorization check for account ownership.
        body = json.dumps(account).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

print("Local IDOR lab: http://127.0.0.1:3002")
ThreadingHTTPServer(("127.0.0.1", 3002), Handler).serve_forever()
