import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.providers.registry import normalize_provider_error  # noqa: E402


class ProviderErrorTests(unittest.TestCase):
    def test_gemini_quota_error_is_short_and_retryable(self) -> None:
        original = RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded; retryDelay: '30s'; secret upstream payload")
        normalized = normalize_provider_error("gemini", original)

        self.assertEqual(normalized.code, "quota_exhausted")
        self.assertTrue(normalized.retryable)
        self.assertEqual(normalized.retry_after_seconds, 30)
        self.assertNotIn("secret upstream payload", str(normalized))
        self.assertIn("자동 Provider 대체는 수행하지 않았습니다", str(normalized))

    def test_other_provider_error_does_not_expose_original_message(self) -> None:
        normalized = normalize_provider_error("openai", RuntimeError("sensitive response body"))

        self.assertEqual(normalized.code, "provider_error")
        self.assertFalse(normalized.retryable)
        self.assertNotIn("sensitive response body", str(normalized))


if __name__ == "__main__":
    unittest.main()
