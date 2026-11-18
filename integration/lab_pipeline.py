import argparse
import fcntl
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from integration.run_workspace import create_workspace

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "local_ai_data"
DATA.mkdir(exist_ok=True)


def run(command):
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False
    )

    if result.stdout:
        print(result.stdout, flush=True)

    if result.stderr:
        print(result.stderr, file=sys.stderr, flush=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: "
            f"{command!r}"
        )

    return result.stdout


def extract_review(output):
    decoder = json.JSONDecoder()

    for line in output.splitlines():
        if not line.startswith("{"):
            continue

        try:
            start = output.index(line)
            result, _ = decoder.raw_decode(output[start:])

            if isinstance(result, dict) and "id" in result:
                return result
        except json.JSONDecodeError:
            continue

    raise RuntimeError("AI review JSON not found")


def execute(task_id):
    workspace = create_workspace(task_id)

    # The current AI CLI uses shared output files.
    # Serialize pipelines until per-run AI storage is added.
    lock_path = DATA / "lab-pipeline.lock"

    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)

        manifest_path = workspace / "manifest.json"
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

        try:
            manifest["status"] = "running"
            manifest_path.write_text(
                json.dumps(manifest, indent=2),
                encoding="utf-8"
            )

            output = run([
                sys.executable,
                "lab/compare_idor.py",
                "--output-dir",
                str(workspace),
                "--ai"
            ])

            review = extract_review(output)
            review_id = review["id"]

            if not isinstance(review_id, str) or not review_id:
                raise RuntimeError("Invalid review ID")

            (workspace / "ai-result.json").write_text(
                json.dumps(review, indent=2),
                encoding="utf-8"
            )

            draft = DATA / "report-draft.md"
            draft.unlink(missing_ok=True)

            run([
                sys.executable,
                "-m",
                "local_ai.cli",
                "report",
                review_id
            ])

            if not draft.is_file():
                raise RuntimeError("Report not generated")

            shutil.copy2(draft, workspace / "report.md")

            from integration.ai_evidence_validator import (
                validate_files, report_section
            )
            validation = validate_files(
                workspace / "idor-comparison.json",
                workspace / "ai-result.json"
            )
            # Preserve evidence: append the assessment only to the draft report
            # before existing SHA-256 sealing; existing archives stay untouched.
            with (workspace / "report.md").open("a", encoding="utf-8") as report_file:
                report_file.write(report_section(validation))
            print("AI EVIDENCE VALIDATOR:", validation["status"])
            for issue in validation["ai_claims_flagged"]:
                print("AI CLAIM FLAGGED:", issue)

            shutil.copy2(
                workspace / "idor-comparison.json",
                workspace / "evidence.json"
            )

            shutil.copy2(
                workspace / "idor-comparison-review.json",
                workspace / "ai-review.json"
            )

            manifest.update({
                "status": "completed",
                "review_id": review_id,
                "finished_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "files": [
                    "evidence.json",
                    "ai-review.json",
                    "ai-result.json",
                    "report.md"
                ],
                "human_review_required": True,
                "external_submission_allowed": False
            })

            from integration.evidence_integrity import seal

            seal(workspace.name)

            print("\nLAB PIPELINE COMPLETED")
            print("Task:", workspace.name)
            print("Review:", review_id)
            print("Workspace:", workspace)

        except Exception as exc:
            manifest["status"] = "failed"
            manifest["error"] = str(exc)
            raise

        finally:
            manifest_path.write_text(
                json.dumps(manifest, indent=2),
                encoding="utf-8"
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id")
    args = parser.parse_args()
    execute(args.task_id)


if __name__ == "__main__":
    main()
