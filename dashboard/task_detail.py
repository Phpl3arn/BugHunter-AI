import html
import json
import re
from pathlib import Path

from integration.task_manager import connect

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "local_ai_data"
RUNS = DATA / "runs"
LOGS = DATA / "task_logs"

VALID_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")

FILES = (
    ("manifest.json", "Görev Bilgileri"),
    ("evidence.json", "HTTP Kanıtları"),
    ("ai-result.json", "Ollama Değerlendirmesi"),
    ("report.md", "Güvenlik Raporu"),
)


def escape(value):
    return html.escape(str(value), quote=True)


def read_limited(path, limit=100000):
    if not path.is_file():
        return "Bu görev için dosya bulunamadı."

    with path.open("rb") as handle:
        size = path.stat().st_size
        if size > limit:
            handle.seek(-limit, 2)
        content = handle.read().decode(
            "utf-8", errors="replace"
        )

    if path.suffix == ".json":
        try:
            content = json.dumps(
                json.loads(content),
                ensure_ascii=False,
                indent=2,
            )
        except ValueError:
            pass

    return content


def render(task_id):
    if not VALID_ID.fullmatch(task_id):
        return None

    with connect() as db:
        task = db.execute(
            """SELECT id, task_type, status, created_at
               FROM tasks WHERE id = ?""",
            (task_id,),
        ).fetchone()

    if task is None:
        return None

    _, task_type, status, created = task
    folder = RUNS / task_id

    sections = []

    for filename, title in FILES:
        content = read_limited(folder / filename)
        sections.append(
            f"<details open>"
            f"<summary>{escape(title)}</summary>"
            f"<pre>{escape(content)}</pre>"
            f"</details>"
        )

    log = read_limited(LOGS / f"{task_id}.log")
    sections.append(
        "<details>"
        "<summary>Çalışma Günlüğü</summary>"
        f"<pre>{escape(log)}</pre>"
        "</details>"
    )

    content = "\n".join(sections)

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BugHunter AI | Görev</title>
<style>
body {{
    margin:0;
    background:#0b1020;
    color:#e5e7eb;
    font:15px system-ui,sans-serif;
}}
main {{
    max-width:1100px;
    margin:35px auto;
    padding:20px;
}}
a {{color:#7dd3fc;text-decoration:none}}
p {{color:#94a3b8}}
details {{
    background:#172033;
    border:1px solid #29364c;
    border-radius:12px;
    margin:16px 0;
    padding:18px;
}}
summary {{
    cursor:pointer;
    font-size:17px;
    font-weight:600;
}}
pre {{
    white-space:pre-wrap;
    overflow-wrap:anywhere;
    line-height:1.6;
    font-size:13px;
}}
</style>
</head>
<body>
<main>
<a href="/">← Dashboard'a dön</a>
<h1>Görev: {escape(task_id)}</h1>
<p>
Tür: {escape(task_type)} |
Durum: {escape(status)} |
Tarih: {escape(created)}
</p>
<p>Yerel sentetik laboratuvar.
AI değerlendirmesi insan incelemesi gerektirir.</p>
{content}
</main>
</body>
</html>"""
