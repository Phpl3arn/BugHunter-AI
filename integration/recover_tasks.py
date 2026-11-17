import argparse
import sqlite3
from datetime import datetime, timedelta, timezone

from integration.task_manager import DB, connect


def recover(older_minutes=30, apply=False):
    if older_minutes < 1:
        raise ValueError("Minimum age must be 1 minute")

    cutoff = (
        datetime.now(timezone.utc) -
        timedelta(minutes=older_minutes)
    ).isoformat()

    with connect() as db:
        db.execute("BEGIN IMMEDIATE")

        rows = db.execute("""
            SELECT id, started_at
            FROM tasks
            WHERE status = 'running'
              AND started_at IS NOT NULL
              AND started_at < ?
            ORDER BY started_at
        """, (cutoff,)).fetchall()

        for task_id, started_at in rows:
            print(f"Stale task: {task_id} | started: {started_at}")

        if apply:
            for task_id, _ in rows:
                db.execute("""
                    UPDATE tasks
                    SET status = 'failed',
                        finished_at = ?,
                        error = 'Marked stale after manual review'
                    WHERE id = ? AND status = 'running'
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    task_id
                ))
            print(f"Marked failed: {len(rows)}")
        else:
            db.rollback()
            print(f"Dry run: {len(rows)} candidate(s), no changes")

    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--older-minutes", type=int, default=30)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    recover(args.older_minutes, args.apply)


if __name__ == "__main__":
    main()
