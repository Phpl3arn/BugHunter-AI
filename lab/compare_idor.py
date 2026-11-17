import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "local_ai_data"
OUT.mkdir(exist_ok=True)

def fetch(port, user):
    url = f"http://127.0.0.1:{port}/api/account?id=1"
    headers = {"X-Demo-User": user} if user else {}
    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=10) as r:
            return {
                "status": r.status,
                "body": r.read().decode("utf-8")
            }
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": ""}

def json_body(result):
    try:
        return json.loads(result["body"])
    except (ValueError, TypeError):
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ai", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    global OUT
    if args.output_dir is not None:
        OUT = args.output_dir.resolve()
        OUT.mkdir(parents=True, exist_ok=True)

    results = {}

    for name, port in [("vulnerable", 3002), ("safe", 3003)]:
        print(f"Testing {name} lab on port {port}...", flush=True)

        results[name] = {
            "alice": fetch(port, "alice"),
            "bob": fetch(port, "bob"),
            "anonymous": fetch(port, None),
        }

    vulnerable = results["vulnerable"]
    safe = results["safe"]

    confirmed = (
        vulnerable["alice"]["status"] == 200
        and vulnerable["bob"]["status"] == 200
        and vulnerable["anonymous"]["status"] == 401
        and json_body(vulnerable["alice"]) is not None
        and json_body(vulnerable["alice"])
            == json_body(vulnerable["bob"])
        and json_body(vulnerable["alice"]).get("owner") == "alice"
        and safe["alice"]["status"] == 200
        and safe["bob"]["status"] == 403
        and safe["anonymous"]["status"] == 401
    )

    comparison = {
        "environment": "local_lab",
        "authorized": True,
        "synthetic_data": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vulnerable_lab": results["vulnerable"],
        "safe_lab": results["safe"],
        "deterministic_test_passed": confirmed,
        "human_review_required": True,
        "external_report_ready": False,
    }

    comparison_file = OUT / "idor-comparison.json"
    comparison_file.write_text(
        json.dumps(comparison, indent=2),
        encoding="utf-8"
    )

    print("\nComparison saved:", comparison_file)
    print("Vulnerable Bob:", vulnerable["bob"]["status"])
    print("Safe Bob:", safe["bob"]["status"])
    print("Deterministic verification:", confirmed)

    if not confirmed:
        print("Verification failed or inconclusive. AI skipped.")
        sys.exit(1)

    evidence = []
    for label, user in [("alice", "alice"), ("bob", "bob")]:
        result = vulnerable[label]
        evidence.append({
            "label": label,
            "request": (
                "GET /api/account?id=1 HTTP/1.1\n"
                "Host: 127.0.0.1:3002\n"
                f"X-Demo-User: {user}"
            ),
            "response": (
                f"HTTP/1.1 {result['status']}\n\n"
                f"{result['body']}"
            )
        })

    evidence.append({
        "label": "safe_control",
        "request": (
            "GET /api/account?id=1 HTTP/1.1\n"
            "Host: 127.0.0.1:3003\n"
            "X-Demo-User: bob"
        ),
        "response": f"HTTP/1.1 {safe['bob']['status']}"
    })

    review = {
        "environment": "local_lab",
        "authorized": True,
        "target": "127.0.0.1",
        "observation": (
            "Self-owned synthetic IDOR laboratory. "
            "In the vulnerable version Bob accesses Alice's "
            "account with HTTP 200. In the safe version "
            "the same access is denied with HTTP 403. "
            "Anonymous requests return HTTP 401. "
            "Authentication uses simulated X-Demo-User headers."
        ),
        "evidence": evidence,
        "notes": (
            "Recorded HTTP results reconstructed into evidence "
            "pairs, not raw packet captures. Synthetic training "
            "data only. Not for external bug bounty submission."
        ),
        "human_review_required": True,
        "external_report_ready": False,
    }

    review_file = OUT / "idor-comparison-review.json"
    review_file.write_text(
        json.dumps(review, indent=2),
        encoding="utf-8"
    )

    print("AI review input:", review_file)

    if args.ai:
        subprocess.run(
            [
                sys.executable,
                "-m", "local_ai.cli",
                "analyze",
                str(review_file)
            ],
            cwd=ROOT,
            check=True
        )

if __name__ == "__main__":
    main()
