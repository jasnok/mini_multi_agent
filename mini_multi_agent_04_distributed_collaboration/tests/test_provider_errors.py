import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.providers.registry import normalize_provider_error  # noqa: E402


class ProviderErrorTests(unittest.TestCase):
    def test_server_error_keeps_safe_diagnostics(self) -> None:
        class ServerError(Exception):
            code = 503
            message = "Service unavailable; api_key=private-value"

        error = normalize_provider_error("gemini", ServerError("request may contain secrets"))
        self.assertIn("HTTP 503", str(error))
        self.assertIn("Service unavailable", str(error))
        self.assertNotIn("private-value", str(error))
        self.assertNotIn("request may contain secrets", str(error))
        self.assertTrue(error.retryable)

    def test_gemini_quota_error_is_normalized(self) -> None:
        error = normalize_provider_error("gemini", RuntimeError("429 RESOURCE_EXHAUSTED retryDelay: '30s' private"))
        self.assertEqual(error.code, "quota_exhausted")
        self.assertEqual(error.retry_after_seconds, 30)
        self.assertNotIn("private", str(error))


if __name__ == "__main__": unittest.main()
