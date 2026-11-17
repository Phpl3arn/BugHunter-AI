import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "local_ai_data"
RUNS = DATA / "runs"

FILES = {
    "idor-comparison.json": "evidence.json",
    "idor-comparison-review.json": "ai-review.json",
    "report-draft.md": "report.md",
}

def archive(task_id):
    if not task_id or not all(
        c.isascii() and (c.isalnum() or c in "-_")
        for c in task_id
    ):
        raise ValueError("Invalid task ID")

    destination = RUNS / task_id

    if destination.exists():
        raise FileExistsError(
            f"Archive already exists: {destination}"
        )

    destination.mkdir(parents=True)

    copied = []

    for source_name, target_name in FILES.items():
        source = DATA / source_name

        if source.is_file():
            shutil.copy2(source, destination / target_name)
            copied.append(target_name)

    log = DATA / "task_logs" / f"{task_id}.log"

    if log.is_file():
        shutil.copy2(log, destination / "execution.log")
        copied.append("execution.log")

    manifest = {
        "task_id": task_id,
        "environment": "local_lab",
        "archived_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "files": copied,
        "human_review_required": True,
        "external_submission_allowed": False,
    }

    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

    print("Archive created:", destination)
    print("Files:", ", ".join(copied))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    args = parser.parse_args()

    archive(args.task_id)

if __name__ == "__main__":
    main()
