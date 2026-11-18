"""BugHunter local-only security research scenarios and human review workflow.

Synthetic exercises only: no outbound requests, DNS lookups, or target scanning.
The legacy IDOR task queue remains unchanged.
"""
import argparse
import hashlib
import html
import ipaddress
import json
import re
import secrets
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'local_ai_data' / 'research_suite'
SCENARIOS = ('idor', 'xss', 'ssrf', 'access')
TASK_ID = re.compile(r'[a-f0-9]{16}\Z')
STATUSES = ('draft', 'in_review', 'approved', 'rejected')
SENTINEL = '<img src=x onerror=alert(1)>'


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def enforce_scope(url):
    """Return approved literal-loopback URL; reject all external or ambiguous URLs."""
    if not isinstance(url, str) or len(url) > 300:
        raise ValueError('Invalid URL')
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise ValueError('Invalid URL') from exc
    if parts.scheme != 'http' or port not in (3002, 3003):
        raise ValueError('Only local HTTP labs on ports 3002/3003 are in scope')
    if parts.username or parts.password or parts.fragment or not parts.hostname:
        raise ValueError('Credentials and fragments are forbidden')
    try:
        address = ipaddress.ip_address(parts.hostname)
    except ValueError as exc:
        raise ValueError('Only literal loopback IPs allowed; no DNS') from exc
    if not address.is_loopback:
        raise ValueError('Out of scope: not a loopback address')
    if parts.path not in ('/api/account', '/', '') or parts.query not in ('', 'id=1'):
        raise ValueError('Only approved local lab paths allowed')
    return url


def synthetic_case(name):
    """Evaluate a controlled, in-memory vulnerable/safe behavior pair."""
    if name not in SCENARIOS:
        raise ValueError('Unknown scenario')
    if name == 'idor':
        vulnerable = {'status': 200, 'owner': 'alice', 'viewer': 'bob'}
        safe = {'status': 403, 'owner': 'alice', 'viewer': 'bob'}
        passed = vulnerable['status'] == 200 and safe['status'] == 403
        explanation = 'Bob can read Alice\'s synthetic account in the vulnerable model; safe model denies it.'
    elif name == 'xss':
        vulnerable = {'input': SENTINEL, 'rendered': SENTINEL}
        safe = {'input': SENTINEL, 'rendered': html.escape(SENTINEL, quote=True)}
        passed = SENTINEL in vulnerable['rendered'] and SENTINEL not in safe['rendered']
        explanation = 'Unescaped HTML is reflected by the toy renderer; the safe renderer encodes it.'
    elif name == 'ssrf':
        target = 'http://169.254.169.254/latest/meta-data/'
        vulnerable = {'url': target, 'simulated_response': 'MOCK_METADATA'}
        safe = {'url': target, 'decision': 'blocked'}
        passed = vulnerable['simulated_response'] == 'MOCK_METADATA' and safe['decision'] == 'blocked'
        explanation = 'A synthetic client accepts a mock metadata URL; the safe policy blocks it. No request is sent.'
    else:
        vulnerable = {'user_role': 'reader', 'resource': 'admin_only', 'status': 200}
        safe = {'user_role': 'reader', 'resource': 'admin_only', 'status': 403}
        passed = vulnerable['status'] == 200 and safe['status'] == 403
        explanation = 'A reader reaches an admin-only synthetic object; role-aware control denies it.'
    return {
        'scenario': name, 'environment': 'local_lab', 'authorized': True,
        'synthetic': True, 'external_submission_allowed': False,
        'vulnerable': vulnerable, 'safe': safe,
        'deterministic_test_passed': bool(passed),
        'explanation': explanation,
    }


def evaluate_ai(evidence, ai_claim=None):
    """Constrain the LLM to an advisory role; compare its claims against evidence."""
    if not isinstance(evidence, dict) or evidence.get('environment') != 'local_lab':
        raise ValueError('Local lab evidence required')
    is_pass = evidence.get('deterministic_test_passed') is True
    issues = []
    if ai_claim:
        lower = str(ai_claim).lower()
        if any(term in lower for term in ('confirmed real', 'production', 'submit bounty', 'externally verified')):
            issues.append('AI claims external verification unsupported by synthetic evidence')
        if 'sanitize' in lower and evidence.get('scenario') in ('idor', 'access'):
            issues.append('Authorization must be checked server-side for each object')
    return {
        'status': 'needs_human_review' if is_pass else 'insufficient_evidence',
        'deterministic_test_passed': is_pass,
        'ai_claim': str(ai_claim or '')[:2000],
        'ai_disagreements': issues,
        'human_review_required': True,
        'external_submission_allowed': False,
    }


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def folder_for(task_id, root=DATA):
    if not TASK_ID.fullmatch(task_id):
        raise ValueError('Invalid research ID')
    return Path(root) / task_id


def ask_local_ollama(evidence, model='qwen2.5-coder:3b'):
    """Optional advisory analysis. Calls only the fixed local Ollama endpoint."""
    if not isinstance(model, str) or not re.fullmatch(r'[a-zA-Z0-9_.:/-]{1,80}', model):
        raise ValueError('Invalid local model name')
    prompt = (
        'Review this SYNTHETIC, self-owned laboratory evidence. '
        'Do not claim a real vulnerability or recommend unauthorized tests. '
        'Explain briefly the distinction between observation and authorization.\n'
        + json.dumps(evidence, ensure_ascii=False)
    )
    payload = {'model': model, 'stream': False, 'format': 'json',
               'messages': [{'role': 'user', 'content': prompt}],
               'options': {'temperature': 0}}
    request = urllib.request.Request(
        'http://127.0.0.1:11434/api/chat',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(request, timeout=120) as response:
        answer = json.load(response)
    return str(answer['message']['content'])[:2000]


def create(name, root=DATA, ai_claim=None, use_ollama=False):
    enforce_scope('http://127.0.0.1:3002/api/account?id=1')
    evidence = synthetic_case(name)
    if use_ollama:
        ai_claim = ask_local_ollama(evidence)
    assessment = evaluate_ai(evidence, ai_claim)
    task_id = secrets.token_hex(8)
    folder = folder_for(task_id, root)
    folder.mkdir(parents=True, exist_ok=False)
    for filename, payload in (('evidence.json', evidence), ('assessment.json', assessment)):
        (folder / filename).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    report = (
        '# Synthetic laboratory finding — DRAFT (NOT VERIFIED)\n\n'
        f'Scenario: {name.upper()}\n\n{evidence["explanation"]}\n\n'
        'Synthetic data only. Human review required. External submission prohibited.\n'
    )
    (folder / 'report.md').write_text(report, encoding='utf-8')
    seal = {'algorithm': 'SHA-256', 'files': {file: digest(folder / file)
            for file in ('evidence.json', 'assessment.json', 'report.md')}}
    (folder / 'integrity.json').write_text(json.dumps(seal, indent=2), encoding='utf-8')
    state = {'status': 'draft', 'created_at': timestamp(), 'events': [],
             'human_review_required': True, 'external_submission_allowed': False}
    (folder / 'review-state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
    return task_id


def verify(task_id, root=DATA):
    folder = folder_for(task_id, root)
    seal = json.loads((folder / 'integrity.json').read_text(encoding='utf-8'))
    if seal.get('algorithm') != 'SHA-256':
        return False
    hashes = seal.get('files')
    expected = {'evidence.json', 'assessment.json', 'report.md'}
    if not isinstance(hashes, dict) or set(hashes) != expected:
        return False
    return all((folder / name).is_file() and digest(folder / name) == hash_value
               for name, hash_value in hashes.items())


def transition(task_id, action, reviewer, note, root=DATA):
    """Human-only review state transitions; never authorizes external publishing."""
    if action not in ('submit', 'approve', 'reject'):
        raise ValueError('Unsupported action')
    if not isinstance(reviewer, str) or len(reviewer.strip()) < 3:
        raise ValueError('Named human reviewer required')
    if not isinstance(note, str) or len(note.strip()) < 10:
        raise ValueError('Review rationale must be at least 10 characters')
    if not verify(task_id, root):
        raise ValueError('Evidence integrity verification failed')
    folder = folder_for(task_id, root)
    path = folder / 'review-state.json'
    state = json.loads(path.read_text(encoding='utf-8'))
    prior = state['status']
    allowed = {('draft', 'submit'): 'in_review',
               ('in_review', 'approve'): 'approved',
               ('in_review', 'reject'): 'rejected'}
    new = allowed.get((prior, action))
    if new is None:
        raise ValueError(f'Invalid transition: {prior} -> {action}')
    state['status'] = new
    state['events'].append({'time': timestamp(), 'action': action,
                            'reviewer': reviewer.strip(), 'note': note.strip()})
    state['external_submission_allowed'] = False
    # Atomic replacement prevents partially written JSON on interruption.
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8')
    temp.replace(path)
    return new


def status(task_id, root=DATA):
    folder = folder_for(task_id, root)
    state = json.loads((folder / 'review-state.json').read_text(encoding='utf-8'))
    return {'id': task_id, 'review_status': state['status'],
            'integrity': 'PASS' if verify(task_id, root) else 'FAIL',
            'external_submission_allowed': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Safe synthetic security research suite')
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run')
    run.add_argument('scenario', choices=SCENARIOS)
    run.add_argument('--ai-claim', default=None, help='Optional model text to cross-check')
    run.add_argument('--ollama', action='store_true', help='Ask only the local Ollama service for advisory text')
    check = sub.add_parser('check')
    check.add_argument('id')
    for action in ('submit', 'approve', 'reject'):
        cmd = sub.add_parser(action)
        cmd.add_argument('id')
        cmd.add_argument('--reviewer', required=True)
        cmd.add_argument('--note', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'run':
            task_id = create(args.scenario, ai_claim=args.ai_claim, use_ollama=args.ollama)
            print(json.dumps(status(task_id), ensure_ascii=False, indent=2))
        elif args.command == 'check':
            print(json.dumps(status(args.id), ensure_ascii=False, indent=2))
        else:
            new = transition(args.id, args.command, args.reviewer, args.note)
            print(f'Review state: {new} (external submission remains disabled)')
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
