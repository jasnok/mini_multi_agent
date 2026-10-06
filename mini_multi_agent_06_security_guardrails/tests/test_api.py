import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.main import health  # noqa: E402
from app.schemas.contracts import GuardrailRunRequest  # noqa: E402


class ApiTests(unittest.TestCase):
    def test_health_identifies_project(self) -> None:
        self.assertEqual(health(), {"status": "ok", "project": "mini_multi_agent_06_security_guardrails"})

    def test_integrated_guardrail_has_no_save_approval_fields(self) -> None:
        self.assertNotIn("approve_save", GuardrailRunRequest.model_fields)
        self.assertNotIn("idempotency_key", GuardrailRunRequest.model_fields)


if __name__ == "__main__": unittest.main()
