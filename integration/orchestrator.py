import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(command):
    print("\nRunning:", " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()

    if not args.mock:
        parser.error("Only --mock mode is supported.")

    runs = Path.home() / "bughunter-runs"
    runs.mkdir(parents=True, exist_ok=True)

    # Her calistirmada yeni ve kalici bir dizin
    base = Path(tempfile.mkdtemp(prefix="run-", dir=runs))

    print("Run directory:", base)

    run([
        sys.executable,
        "engine/engine.py",
        "--scope", "engine/engagement.example.json",
        "--base", str(base),
        "--mock",
        "--hunt",
    ])

    report = base / "demo-local" / "report.md"

    if not report.is_file() or report.stat().st_size == 0:
        raise SystemExit("New engine report missing or empty.")

    run([
        sys.executable,
        "-m", "integration.mock_bridge",
        "--report", str(report),
        "--analyze",
    ])

    print("\nMock pipeline completed successfully.")
    print("Run saved at:", base)

if __name__ == "__main__":
    main()
