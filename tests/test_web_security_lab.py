import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

from lab.web_security_lab import make_server


class WebSecurityLabTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.servers = [
            make_server(True),
            make_server(False),
        ]
        cls.threads = []

        for server in cls.servers:
            thread = threading.Thread(
                target=server.serve_forever,
                daemon=True,
            )
            thread.start()
            cls.threads.append(thread)

    @classmethod
    def tearDownClass(cls):
        for server in cls.servers:
            server.shutdown()
            server.server_close()
        for thread in cls.threads:
            thread.join(timeout=3)

    def request(self, safe, path, headers=None):
        server = self.servers[1 if safe else 0]
        url = f"http://127.0.0.1:{server.server_port}{path}"
        request = urllib.request.Request(url, headers=headers or {})

        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, response.read().decode()
        except urllib.error.HTTPError as error:
            try:
                return error.code, error.read().decode()
            finally:
                error.close()

    def test_xss_reflection(self):
        payload = '<script>alert(1)</script>'
        encoded = urllib.parse.quote(payload)

        vulnerable = self.request(False, "/reflect?value=" + encoded)
        safe = self.request(True, "/reflect?value=" + encoded)

        self.assertEqual(vulnerable[0], 200)
        self.assertIn(payload, vulnerable[1])
        self.assertEqual(safe[0], 200)
        self.assertNotIn(payload, safe[1])
        self.assertIn("&lt;script&gt;", safe[1])

    def test_access_control(self):
        headers = {"X-Demo-Role": "reader"}

        vulnerable = self.request(False, "/admin", headers)
        safe = self.request(True, "/admin", headers)

        self.assertEqual(vulnerable[0], 200)
        self.assertEqual(safe[0], 403)

    def test_local_ssrf_like_behavior(self):
        vulnerable = self.request(False, "/fetch?target=internal")
        safe = self.request(True, "/fetch?target=internal")

        self.assertEqual(vulnerable[0], 200)
        self.assertIn("MOCK_INTERNAL_METADATA", vulnerable[1])
        self.assertEqual(safe[0], 403)

    def test_external_target_rejected(self):
        path = "/fetch?target=" + urllib.parse.quote(
            "http://example.com", safe=""
        )

        for safe in (False, True):
            with self.subTest(safe=safe):
                status, _ = self.request(safe, path)
                self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
