"""Collect repeatable HTTP evidence from owned ephemeral loopback labs."""

import argparse
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from lab.web_security_lab import make_server

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "local_ai_data" / "http_evidence"

SCENARIOS = ("xss", "ssrf", "access")


def probe(port, path, headers):
    url = f"http://127.0.0.1:{port}{path}"
    request = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({})
    )

    try:
        with opener.open(request, timeout=3) as response:
            status = response.status
            body = response.read(4096).decode("utf-8")
    except urllib.error.HTTPError as error:
        try:
            status = error.code
            body = error.read(4096).decode("utf-8")
        finally:
            error.close()

    return {
        "request": {
            "method": "GET",
            "path": path,
            "headers": headers,
        },
        "response": {
            "status": status,
            "body": body,
        },
    }


def collect(scenario):
    if scenario not in SCENARIOS:
        raise ValueError("Unsupported local scenario")

    vulnerable = make_server(True)
    safe = make_server(False)
    servers = (vulnerable, safe)
    threads = []

    try:
        for server in servers:
            thread = threading.Thread(
                target=server.serve_forever,
                daemon=True,
            )
            thread.start()
            threads.append(thread)

        if scenario == "xss":
            payload = "<script>alert(1)</script>"
            path = "/reflect?value=" + urllib.parse.quote(
                payload, safe=""
            )
            headers = {}

        elif scenario == "ssrf":
            path = "/fetch?target=internal"
            headers = {}

        else:
            path = "/admin"
            headers = {"X-Demo-Role": "reader"}

        bad = probe(vulnerable.server_port, path, headers)
        good = probe(safe.server_port, path, headers)

        b = bad["response"]
        g = good["response"]

        if scenario == "xss":
            passed = (
                b["status"] == 200
                and g["status"] == 200
                and payload in b["body"]
                and payload not in g["body"]
                and "&lt;script&gt;" in g["body"]
            )
        elif scenario == "ssrf":
            passed = (
                b["status"] == 200
                and "MOCK_INTERNAL_METADATA" in b["body"]
                and g["status"] == 403
            )
        else:
            passed = (
                b["status"] == 200
                and "SYNTHETIC_ADMIN_RESOURCE" in b["body"]
                and g["status"] == 403
            )

        return {
            "scenario": scenario,
            "environment": "local_lab",
            "evidence_type": "live_http",
            "authorized": True,
            "synthetic": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vulnerable": bad,
            "safe": good,
            "deterministic_test_passed": bool(passed),
            "human_review_required": True,
            "external_submission_allowed": False,
        }

    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=SCENARIOS)
    args = parser.parse_args()

    result = collect(args.scenario)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / f"{args.scenario}-evidence.json"
    path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("Evidence saved:", path)

    if not result["deterministic_test_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
