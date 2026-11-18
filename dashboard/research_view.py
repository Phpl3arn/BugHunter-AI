"""Read-only dashboard views for local Research Suite."""
import html
import json

from integration import research_suite as rs


def esc(value):
    return html.escape(str(value), quote=True)


def load_record(task_id):
    if not rs.TASK_ID.fullmatch(task_id):
        return None

    folder = rs.folder_for(task_id)
    if not folder.is_dir():
        return None

    try:
        evidence = json.loads(
            (folder / "evidence.json").read_text(encoding="utf-8")
        )
        state = json.loads(
            (folder / "review-state.json").read_text(encoding="utf-8")
        )
        assessment = json.loads(
            (folder / "assessment.json").read_text(encoding="utf-8")
        )
        integrity = "PASS" if rs.verify(task_id) else "FAIL"

        return {
            "id": task_id,
            "scenario": evidence["scenario"],
            "status": state["status"],
            "integrity": integrity,
            "evidence": evidence,
            "assessment": assessment,
            "state": state,
        }
    except (OSError, ValueError, KeyError, TypeError):
        return None


def listing():
    records = []

    if rs.DATA.is_dir():
        for folder in sorted(
            rs.DATA.iterdir(),
            key=lambda p: p.name,
            reverse=True,
        ):
            if folder.is_dir() and rs.TASK_ID.fullmatch(folder.name):
                record = load_record(folder.name)
                if record:
                    records.append(record)

    rows = []
    for record in records[:100]:
        task_id = record["id"]
        integrity = record["integrity"]
        color = "#4ade80" if integrity == "PASS" else "#f87171"

        rows.append(
            "<tr>"
            f'<td><a href="/research/{task_id}">{esc(task_id)}</a></td>'
            f'<td>{esc(record["scenario"].upper())}</td>'
            f'<td>{esc(record["status"])}</td>'
            f'<td style="color:{color}">{esc(integrity)}</td>'
            "</tr>"
        )

    if not rows:
        rows.append('<tr><td colspan="4">Araştırma yok</td></tr>')

    return (
        '<div class="card">'
        '<h2>Research Suite — Yerel Araştırmalar</h2>'
        '<div class="scroll"><table>'
        '<thead><tr><th>Araştırma ID</th><th>Senaryo</th>'
        '<th>İnceleme</th><th>Bütünlük</th></tr></thead>'
        '<tbody>' + "".join(rows) + '</tbody></table></div></div>'
    )


def detail(task_id):
    record = load_record(task_id)
    if record is None:
        return None

    sections = []
    for title, key in (
        ("Kanıtlar", "evidence"),
        ("AI / Kanıt Değerlendirmesi", "assessment"),
        ("İnceleme Geçmişi", "state"),
    ):
        content = json.dumps(
            record[key], ensure_ascii=False, indent=2
        )
        sections.append(
            f"<details open><summary>{esc(title)}</summary>"
            f"<pre>{esc(content)}</pre></details>"
        )

    folder = rs.folder_for(task_id)
    try:
        report = (folder / "report.md").read_text(
            encoding="utf-8"
        )
    except OSError:
        report = "Rapor bulunamadı."

    sections.append(
        f"<details open><summary>Rapor Taslağı</summary>"
        f"<pre>{esc(report)}</pre></details>"
    )

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BugHunter Research</title>
<style>
body{{background:#0b1020;color:#e5e7eb;font:15px system-ui}}
main{{max-width:1050px;margin:35px auto;padding:20px}}
a{{color:#7dd3fc}}
details{{background:#172033;border:1px solid #29364c;
border-radius:12px;padding:18px;margin:15px 0}}
summary{{cursor:pointer;font-weight:bold}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5}}
</style>
</head>
<body><main>
<a href="/">← Dashboard</a>
<h1>{esc(record["scenario"].upper())} Araştırması</h1>
<p>ID: {esc(task_id)}</p>
<p>İnceleme: {esc(record["status"])}</p>
<p>Kanıt bütünlüğü: {esc(record["integrity"])}</p>
<p>Yalnızca sentetik laboratuvar. Dış rapor gönderimi kapalı.</p>
<form method="post" action="/research/review">
<input type="hidden" name="csrf" value="{__import__('dashboard.server', fromlist=['CSRF_TOKEN']).CSRF_TOKEN}">
<input type="hidden" name="task_id" value="{esc(task_id)}">
<label>İşlem: <select name="action"><option value="submit">İncelemeye gönder</option>
<option value="approve">Yerel araştırmayı onayla</option>
<option value="reject">Reddet</option></select></label>
<label>İnceleyen: <input name="reviewer" required minlength="3" maxlength="80"></label>
<label>Açıklama: <input name="note" required minlength="10" maxlength="500"></label>
<button type="submit">İnsan inceleme işlemini uygula</button>
</form>
{''.join(sections)}
</main></body></html>"""
