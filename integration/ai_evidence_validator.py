"""Conservative checks of local synthetic IDOR AI narrative against recorded HTTP observations.

The validator does not establish vulnerability in real-world targets. Its checks are
heuristics for known dangerous overclaims and the known misleading identity claim.
"""
import json
import re
from pathlib import Path


def _status(record, side, principal):
    return record.get(side, {}).get(principal, {}).get('status')


def _body(record, side, principal):
    try:
        return json.loads(record[side][principal]['body'])
    except (KeyError, TypeError, ValueError):
        return None


def validate(evidence, ai_result):
    """Produce a non-authoritative human-review gate from stored local-lab evidence.

    AI fields are entirely untrusted. No network calls are made.
    """
    if not isinstance(evidence, dict) or not isinstance(ai_result, dict):
        raise ValueError('Expected evidence and AI result mappings')

    supported = (
        evidence.get('environment') == 'local_lab'
        and evidence.get('authorized') is True
        and evidence.get('synthetic_data') is True
        and evidence.get('deterministic_test_passed') is True
        and _status(evidence, 'vulnerable_lab', 'alice') == 200
        and _status(evidence, 'vulnerable_lab', 'bob') == 200
        and _status(evidence, 'vulnerable_lab', 'anonymous') == 401
        and _status(evidence, 'safe_lab', 'alice') == 200
        and _status(evidence, 'safe_lab', 'bob') == 403
        and _status(evidence, 'safe_lab', 'anonymous') == 401
        and _body(evidence, 'vulnerable_lab', 'alice') == _body(evidence, 'vulnerable_lab', 'bob')
        and isinstance(_body(evidence, 'vulnerable_lab', 'bob'), dict)
        and _body(evidence, 'vulnerable_lab', 'bob').get('owner') == 'alice'
    )

    narrative = ' '.join(str(ai_result.get(key, '')) for key in (
        'explanation', 'recommended_next_step', 'hypothesis'
    ))
    low = narrative.casefold()
    issues = []

    if not supported:
        issues.append('Stored HTTP evidence does not satisfy the known local IDOR control conditions')

    # Bob needs to be authenticated as bob, not alice, to demonstrate the flaw.
    impersonate_alice = (
        re.search(r'(?i)x-demo-user\s*[:=]\s*[`\'\"]?alice', narrative) is not None
        and re.search(r'(?i)bob|attacker', narrative) is not None
    )
    if impersonate_alice:
        issues.append('AI confuses user identity: Bob must request Alice object as X-Demo-User: bob, not alice')

    # Object authorization, not input sanitation, is the missing control.
    if any(word in low for word in ('sanitiz', 'sanitize', 'sanitise', 'sanitizasy', 'temizle')) and 'id' in low:
        issues.append('AI suggests parameter sanitization as IDOR fix; require per-object authorization checks')

    if any(phrase in low for phrase in (
        'confirmed production', 'confirmed real-world', 'real production',
        'externally verified', 'submit to bug bounty', 'can be submitted'
    )):
        issues.append('AI overstates synthetic laboratory findings as external verification')

    return {
        'kind': 'local_idor_ai_evidence_check',
        'evidence_supported': bool(supported),
        'status': 'needs_human_review' if supported else 'insufficient_evidence',
        'ai_claims_flagged': issues,
        'ai_narrative_usable_without_correction': bool(supported and not issues),
        'human_review_required': True,
        'external_submission_allowed': False,
        'limitations': 'Heuristic known-claim checks, not general semantic proof or an AI accuracy score.',
    }


def validate_files(evidence_path, result_path):
    evidence = json.loads(Path(evidence_path).read_text(encoding='utf-8'))
    result = json.loads(Path(result_path).read_text(encoding='utf-8'))
    return validate(evidence, result)


def report_section(validation):
    issues = validation['ai_claims_flagged']
    lines = [
        '\n\n## AI Evidence Validation (automatic; local lab only)',
        f"- Evidence supported: {validation['evidence_supported']}",
        f"- Review status: {validation['status']}",
        f"- AI narrative usable without correction: {validation['ai_narrative_usable_without_correction']}",
        '- Human approval required; external submission disabled',
    ]
    if issues:
        lines.append('### AI assertions requiring correction')
        lines.extend(f'- {item}' for item in issues)
    else:
        lines.append('- No known overclaim patterns detected; this is NOT a clean bill of health.')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('evidence')
    parser.add_argument('ai_result')
    args = parser.parse_args(argv)
    print(json.dumps(validate_files(args.evidence, args.ai_result), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
