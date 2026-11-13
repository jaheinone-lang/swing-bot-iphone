"""Offline unit tests for PAPER-only credential checks."""
import unittest
import urllib.error
from swingbot.alpaca_paper_check import HOST, check_paper_connection


class _Response:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): return False


class PaperCheckTests(unittest.TestCase):
    def test_missing_keys_never_call_network(self):
        def fail(*args, **kwargs): raise AssertionError("must not call API")
        result = check_paper_connection(key="", secret="", urlopen=fail)
        self.assertEqual(result["status"], "MISSING_PAPER_KEYS")

    def test_only_paper_get_with_no_body_logged(self):
        def fake(req, timeout):
            self.assertEqual(req.full_url, HOST)
            self.assertEqual(req.get_method(), "GET")
            self.assertEqual(timeout, 12)
            self.assertNotIn("SECRET", req.full_url)
            return _Response()
        result = check_paper_connection(key="demo-id", secret="demo-secret", urlopen=fake)
        self.assertEqual(result, {"status": "PAPER_API_OK", "paper_only": True,
                                  "market_data_requested": False, "orders_sent": False})
        self.assertNotIn("demo", str(result))

    def test_wrong_credentials_status_does_not_expose_secrets(self):
        def fake(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 401, "Bad Credentials", {}, None)
        result = check_paper_connection(key="sensitive-id", secret="sensitive-key", urlopen=fake)
        self.assertEqual(result["status"], "PAPER_API_UNAUTHORIZED")
        self.assertNotIn("sensitive", str(result))

    def test_network_error_is_safe(self):
        def fake(req, timeout):
            raise urllib.error.URLError("secret-like-private-string")
        result = check_paper_connection(key="id", secret="secret", urlopen=fake)
        self.assertEqual(result["status"], "PAPER_API_NETWORK_ERROR")
        self.assertNotIn("private-string", str(result))


if __name__ == "__main__":
    unittest.main()
