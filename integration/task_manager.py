import argparse
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "local_ai_data"
DB = DATA / "tasks.sqlite3"
LOGS = DATA / "task_logs"

def now():
    return datetime.now(timezone.utc).isoformat()

def connect():
    DATA.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=10)
    db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            log_path TEXT,
            error TEXT
        )
    """)
    db.commit()
    return db

def add():
    task_id = uuid.uuid4().hex[:12]

    with connect() as db:
        db.execute(
            """
            INSERT INTO tasks
            (id, task_type, status, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, "local_idor_lab", "queued", now())
        )

    print("Task created:", task_id)
    print("Status: queued")

def list_tasks():
    with connect() as db:
        tasks = db.execute("""
            SELECT id, task_type, status, created_at
            FROM tasks
            ORDER BY created_at DESC
            LIMIT 30
        """).fetchall()

    if not tasks:
        print("No tasks found.")
        return

    for task in tasks:
        print(" | ".join(str(value) for value in task))

def run_next():
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")

        row = db.execute("""
            SELECT id FROM tasks
            WHERE status = 'queued'
            ORDER BY created_at, rowid
            LIMIT 1
        """).fetchone()

        if not row:
            print("No queued tasks.")
            return

        task_id = row[0]

        db.execute("""
            UPDATE tasks
            SET status = 'running', started_at = ?
            WHERE id = ?
        """, (now(), task_id))

    LOGS.mkdir(parents=True, exist_ok=True)
    log_path = LOGS / f"{task_id}.log"

    print("Running task:", task_id, flush=True)

    status = "completed"
    error = None

    try:
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "integration.lab_pipeline",
                    "--task-id",
                    task_id
                ],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=180
            )

        if result.returncode != 0:
            status = "failed"
            error = f"Pipeline exit code: {result.returncode}"

    except subprocess.TimeoutExpired:
        status = "failed"
        error = "Pipeline timed out after 180 seconds"

    except OSError as exc:
        status = "failed"
        error = str(exc)

    with connect() as db:
        db.execute("""
            UPDATE tasks
            SET status = ?,
                finished_at = ?,
                log_path = ?,
                error = ?
            WHERE id = ?
        """, (
            status,
            now(),
            str(log_path),
            error,
            task_id
        ))

    print("Task:", task_id)
    print("Status:", status)
    print("Log:", log_path)

    if error:
        print("Error:", error)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=["add", "list", "run"]
    )
    args = parser.parse_args()

    if args.action == "add":
        add()
    elif args.action == "list":
        list_tasks()
    elif args.action == "run":
        run_next()

if __name__ == "__main__":
    main()
