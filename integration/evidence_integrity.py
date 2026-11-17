import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "local_ai_data" / "runs"
VALID_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")

FILES = (
    "evidence.json",
    "ai-review.json",
    "ai-result.json",
    "report.md",
    "idor-comparison.json",
    "idor-comparison-review.json",
)


def workspace(task_id):
    if not VALID_ID.fullmatch(task_id):
        raise ValueError("Invalid task ID")
    return RUNS / task_id


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seal(task_id):
    folder = workspace(task_id)

    if not folder.is_dir():
        raise FileNotFoundError(folder)

    manifest_path = folder / "integrity.json"
    if manifest_path.exists():
        raise FileExistsError(
            "Integrity record already exists; refusing overwrite"
        )

    hashes = {}
    for name in FILES:
        path = folder / name
        if path.is_file():
            hashes[name] = sha256(path)

    missing = [name for name in FILES if name not in hashes]
    if missing:
        raise ValueError(
            "Cannot seal incomplete evidence: " + ", ".join(missing)
        )

    record = {
        "task_id": task_id,
        "algorithm": "SHA-256",
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "files": hashes,
    }

    with manifest_path.open("x", encoding="utf-8") as file:
        json.dump(record, file, indent=2)

    print(f"SEALED: {task_id} ({len(hashes)} files)")


def verify(task_id):
    folder = workspace(task_id)
    record = json.loads(
        (folder / "integrity.json").read_text(encoding="utf-8")
    )

    if record.get("task_id") != task_id:
        raise ValueError("Task ID mismatch")

    if record.get("algorithm") != "SHA-256":
        raise ValueError("Unsupported algorithm")

    hashes = record["files"]
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("Invalid integrity record")

    all_ok = True

    for name, expected in hashes.items():
        if name not in FILES or not isinstance(expected, str):
            print(f"INVALID ENTRY: {name}")
            all_ok = False
            continue

        path = folder / name
        ok = path.is_file() and sha256(path) == expected

        print(f"{'PASS' if ok else 'FAIL'}: {name}")
        all_ok = all_ok and ok

    return all_ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["seal", "verify"])
    parser.add_argument("task_id")
    args = parser.parse_args()

    if args.action == "seal":
        seal(args.task_id)
    elif not verify(args.task_id):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
