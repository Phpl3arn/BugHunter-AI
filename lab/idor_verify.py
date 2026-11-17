import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

URL = "http://127.0.0.1:3002/api/account?id=1"

def request_as(user):
    headers = {"X-Demo-User": user} if user else {}
    req = urllib.request.Request(URL, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return {
                "status": response.status,
                "body": response.read().decode()
            }
    except urllib.error.HTTPError as error:
        return {
            "status": error.code,
            "body": ""
        }

alice = request_as("alice")
bob = request_as("bob")
anonymous = request_as(None)

alice_data = json.loads(alice["body"]) if alice["status"] == 200 else {}
bob_data = json.loads(bob["body"]) if bob["status"] == 200 else {}

confirmed = (
    alice["status"] == 200
    and bob["status"] == 200
    and anonymous["status"] == 401
    and alice_data.get("owner") == "alice"
    and bob_data == alice_data
)

result = {
    "environment": "local_lab",
    "synthetic_data": True,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "vulnerability": "BOLA / IDOR",
    "url": URL,
    "tests": {
        "owner": alice,
        "other_user": bob,
        "anonymous": {"status": anonymous["status"]}
    },
    "authorization_bypass_observed": confirmed,
    "human_review_required": True,
    "external_report_ready": False
}

output = Path("local_ai_data/idor-lab-evidence.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(
    json.dumps(result, indent=2),
    encoding="utf-8"
)

print(json.dumps(result, indent=2))
print("\nEvidence saved:", output)
