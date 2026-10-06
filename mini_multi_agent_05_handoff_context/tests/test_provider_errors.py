import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.providers.registry import normalize_provider_error  # noqa: E402


class ProviderErrorTests(unittest.TestCase):
    def test_contract_error_reports_field_without_input_value(self) -> None:
        from pydantic import BaseModel, ValidationError

        class Response(BaseModel):
            order_id: int

        try:
            Response(order_id="private-order-value")
        except ValidationError as original:
            error = normalize_provider_error("openai", original)
        else:
            self.fail("Expected a validation error")
        self.assertEqual(error.code, "output_contract_error")
        self.assertIn("order_id", str(error))
        self.assertNotIn("private-order-value", str(error))

    def test_gemini_quota_error_is_normalized(self) -> None:
        error = normalize_provider_error("gemini", RuntimeError("429 RESOURCE_EXHAUSTED retryDelay: '30s' private"))
        self.assertEqual(error.code, "quota_exhausted")
        self.assertEqual(error.retry_after_seconds, 30)
        self.assertNotIn("private", str(error))


if __name__ == "__main__": unittest.main()
