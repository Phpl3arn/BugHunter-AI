import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "local_ai_data"
DATA.mkdir(exist_ok=True)

def run(args, capture=False):
    print("\n>", " ".join(map(str, args)), flush=True)
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )
    if capture:
        print(result.stdout)
    return result.stdout if capture else None

def main():
    # 1. Compare local lab servers
    output = run([
        sys.executable,
        "lab/compare_idor.py",
        "--ai",
    ], capture=True)

    # 2. Extract AI JSON from the final output.
    decoder = json.JSONDecoder()
    review = None

    for line in output.splitlines():
        if line.strip().startswith("{"):
            try:
                obj, _ = decoder.raw_decode(
                    output[output.index(line):]
                )
                if "id" in obj and "status" in obj:
                    review = obj
                    break
            except (json.JSONDecodeError, ValueError):
                pass

    if review is None:
        raise SystemExit("AI review JSON could not be extracted.")

    review_id = review["id"]

    if not isinstance(review_id, str) or not review_id:
        raise SystemExit("Invalid review ID.")

    # 3. Generate a draft through the existing CLI.
    run([
        sys.executable,
        "-m", "local_ai.cli",
        "report", review_id
    ])

    # 4. Archive the report separately.
    source = DATA / "report-draft.md"

    if not source.is_file():
        raise SystemExit("Report draft missing.")

    stamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d-%H%M%S-%f"
    )
    archive = DATA / "reports" / stamp
    archive.mkdir(parents=True, exist_ok=True)

    destination = archive / "report-draft.md"
    destination.write_bytes(source.read_bytes())

    summary = {
        "environment": "local_lab",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "review_id": review_id,
        "status": review.get("status"),
        "deterministic_comparison": "passed",
        "report_path": str(destination),
        "human_review_required": True,
        "external_submission_allowed": False,
    }

    (archive / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8"
    )

    print("\nLAB PIPELINE COMPLETED")
    print("Review ID:", review_id)
    print("Report:", destination)

if __name__ == "__main__":
    main()
