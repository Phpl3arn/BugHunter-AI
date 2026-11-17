"""Import a Claude-BugHunter MOCK report into local_ai as unverified training evidence.

Never executes target requests or presents mock output as a real finding.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


def convert_mock(report_text):
    if '# Engagement report — demo-local' not in report_text:
        raise ValueError('Only the expected demo-local mock report is accepted')
    match = re.search(r'(?m)^##\s+1\.\s+(.+)$', report_text)
    if not match:
        raise ValueError('Expected demo-local finding section not found')
    title = match.group(1).strip()
    if len(title) > 120:
        raise ValueError('Finding title too long')
    # The source report is entirely synthetic. Its assertions are NOT evidence.
    return {
        'environment': 'local_lab',
        'authorized': True,
        'target': 'localhost',
        'observation': ('MOCK / SYNTHETIC report from Claude-BugHunter demo-local. '
                        'The simulated engine emitted finding: ' + title + '. '
                        'No real traffic, request/response captures, or independently validated vulnerability exists.'),
        'evidence': [],
        'notes': 'simulation_only; never submit as a bug bounty report',
    }


def main(argv=None):
    p = argparse.ArgumentParser(description='Import demo-local mock report into the local AI reviewer')
    p.add_argument('--report', default='/tmp/bughunter-test/demo-local/report.md')
    p.add_argument('--output', default='local_ai_data/engine-demo-evidence.json')
    p.add_argument('--analyze', action='store_true', help='Run existing local_ai reviewer via loopback Ollama')
    args = p.parse_args(argv)
    try:
        source = Path(args.report)
        if not source.is_file():
            raise ValueError('Demo report not found; run the engine with --mock first')
        record = convert_mock(source.read_text(encoding='utf-8'))
        dest = Path(args.output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Created synthetic training record:', dest)
        if args.analyze:
            return subprocess.call([sys.executable, '-m', 'local_ai.cli', 'analyze', str(dest)])
    except (OSError, UnicodeError, ValueError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
