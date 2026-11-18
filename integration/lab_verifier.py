"""Deterministic live-HTTP comparison of our two fixed loopback IDOR labs.

No user-supplied targets, DNS, proxy discovery, redirects, or external network.
"""
import argparse
import json
import urllib.error
import urllib.request
from integration.research_suite import enforce_scope


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect refused by local lab policy')


def probe(port, user):
    url = enforce_scope('http://127.0.0.1:%d/api/account?id=1' % port)
    request = urllib.request.Request(url, headers={'X-Demo-User': user})
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect()
    )
    try:
        with opener.open(request, timeout=3) as response:
            return {'status': response.status, 'body': response.read(4096).decode('utf-8')}
    except urllib.error.HTTPError as error:
        return {'status': error.code, 'body': ''}


def compare():
    vulnerable_alice = probe(3002, 'alice')
    vulnerable_bob = probe(3002, 'bob')
    safe_bob = probe(3003, 'bob')
    va = json.loads(vulnerable_alice['body']) if vulnerable_alice['status'] == 200 else {}
    vb = json.loads(vulnerable_bob['body']) if vulnerable_bob['status'] == 200 else {}
    passed = (vulnerable_alice['status'] == 200 and vulnerable_bob['status'] == 200
              and safe_bob['status'] == 403 and va == vb and va.get('owner') == 'alice')
    return {'environment': 'local_lab', 'authorized': True,
            'kind': 'live_http_idor', 'deterministic_test_passed': passed,
            'vulnerable_alice_status': vulnerable_alice['status'],
            'vulnerable_bob_status': vulnerable_bob['status'],
            'safe_bob_status': safe_bob['status'],
            'external_submission_allowed': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    result = compare()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result['deterministic_test_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
