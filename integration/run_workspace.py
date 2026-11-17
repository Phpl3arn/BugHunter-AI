import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "local_ai_data" / "runs"

def create_workspace(task_id=None):
    task_id = task_id or uuid.uuid4().hex[:12]

    if not task_id or not all(
        c.isascii() and (c.isalnum() or c in "-_")
        for c in task_id
    ):
        raise ValueError("Invalid task ID")

    folder = RUNS / task_id
    folder.mkdir(parents=True, exist_ok=False)

    manifest = {
        "task_id": task_id,
        "environment": "local_lab",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "initialized",
        "human_review_required": True,
        "external_submission_allowed": False
    }

    (folder / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

    return folder

if __name__ == "__main__":
    folder = create_workspace()
    print("Workspace created:", folder)
