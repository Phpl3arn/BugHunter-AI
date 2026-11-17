import html
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, quote

from integration.task_manager import connect

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "local_ai_data" / "runs"

HOST = "127.0.0.1"
PORT = 8088

TASK_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


def esc(value):
    return html.escape(str(value if value is not None else ""))


def get_tasks():
    with connect() as db:
        return db.execute("""
            SELECT id, task_type, status, created_at
            FROM tasks
            ORDER BY created_at DESC
            LIMIT 100
        """).fetchall()


def page():
    rows = get_tasks()

    completed = sum(t[2] == "completed" for t in rows)
    failed = sum(t[2] == "failed" for t in rows)
    queued = sum(t[2] == "queued" for t in rows)

    records = []

    for task_id, kind, status, created in rows:
        report = RUNS / task_id / "report.md"

        link = (
            f'<a href="/report/{quote(task_id)}">Raporu Aç</a>'
            if TASK_ID.fullmatch(task_id) and report.is_file()
            else "—"
        )

        records.append(
            "<tr>"
            f"<td><code>{esc(task_id)}</code></td>"
            f"<td>{esc(kind)}</td>"
            f"<td>{esc(status)}</td>"
            f"<td>{esc(created)}</td>"
            f"<td>{link}</td>"
            "</tr>"
        )

    table_rows = "\n".join(records)
    if not table_rows:
        table_rows = '<tr><td colspan="5">Henüz görev yok</td></tr>'

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BugHunter AI</title>
<style>
* {{box-sizing:border-box}}
body {{margin:0;background:#0b1020;color:#e5e7eb;
       font:15px system-ui,Arial,sans-serif}}
main {{max-width:1150px;margin:45px auto;padding:20px}}
h1 {{font-size:30px;margin-bottom:5px}}
p {{color:#94a3b8}}
.stats {{display:grid;grid-template-columns:repeat(3,1fr);
        gap:15px;margin:30px 0}}
.card {{background:#172033;border:1px solid #29364c;
       border-radius:12px;padding:22px}}
.number {{font-size:32px;font-weight:700;margin-top:10px}}
table {{width:100%;border-collapse:collapse;min-width:700px}}
th,td {{padding:15px;text-align:left;border-bottom:1px solid #29364c}}
th {{color:#94a3b8}}
a {{color:#7dd3fc;text-decoration:none}}
.scroll {{overflow-x:auto}}
small {{color:#94a3b8}}
@media(max-width:600px) {{
.stats {{grid-template-columns:1fr}}
}}
</style>
</head>
<body>
<main>
<h1>🛡️ BugHunter AI</h1>
<p>Local Security Research Dashboard</p>
<small>Yalnızca yerel laboratuvar · Salt okunur panel</small>

<section class="stats">
<div class="card">Tamamlanan<div class="number">{completed}</div></div>
<div class="card">Bekleyen<div class="number">{queued}</div></div>
<div class="card">Başarısız<div class="number">{failed}</div></div>
</section>

<div class="card">
<h2>Araştırma Görevleri</h2>
<div class="scroll">
<table>
<thead>
<tr><th>Görev ID</th><th>Tür</th><th>Durum</th>
<th>Oluşturulma</th><th>Rapor</th></tr>
</thead>
<tbody>{table_rows}</tbody>
</table>
</div>
</div>
<p>Veriler SQLite görev kuyruğundan okunur.
Bulgular yalnızca sentetik laboratuvar verileridir.</p>
</main>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'"
        )
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlsplit(self.path).path

        if path == "/":
            try:
                self.respond(200, page(), "text/html; charset=utf-8")
            except Exception:
                self.respond(500, "Dashboard error", "text/plain; charset=utf-8")
            return

        match = re.fullmatch(r"/report/([A-Za-z0-9_-]{1,64})", path)

        if match:
            task_id = match.group(1)

            with connect() as db:
                exists = db.execute(
                    "SELECT 1 FROM tasks WHERE id = ?",
                    (task_id,)
                ).fetchone()

            if not exists:
                self.respond(404, "Not found", "text/plain; charset=utf-8")
                return

            report = RUNS / task_id / "report.md"
            if report.is_file():
                self.respond(
                    200,
                    report.read_text(encoding="utf-8"),
                    "text/plain; charset=utf-8"
                )
                return

        self.respond(404, "Not found", "text/plain; charset=utf-8")


if __name__ == "__main__":
    print(f"BugHunter Dashboard: http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
