import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.providers.registry import normalize_provider_error  # noqa: E402


class ProviderErrorTests(unittest.TestCase):
    def test_gemini_quota_error_is_normalized(self) -> None:
        error = normalize_provider_error("gemini", RuntimeError("429 RESOURCE_EXHAUSTED retryDelay: '30s' private payload"))
        self.assertEqual(error.code, "quota_exhausted")
        self.assertTrue(error.retryable)
        self.assertEqual(error.retry_after_seconds, 30)
        self.assertNotIn("private payload", str(error))


if __name__ == "__main__":
    unittest.main()
