import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.providers.registry import normalize_provider_error  # noqa: E402


class ProviderErrorTests(unittest.TestCase):
    def test_openai_quota_error_is_normalized(self) -> None:
        error = normalize_provider_error("openai", RuntimeError("429 rate limit retry after 20 seconds private"))
        self.assertEqual(error.code, "quota_exhausted")
        self.assertEqual(error.retry_after_seconds, 20)
        self.assertNotIn("private", str(error))


if __name__ == "__main__": unittest.main()
