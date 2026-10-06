import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.enterprise_leak_flow import run_enterprise_data_leak_guard
from app.orchestration.policy_database_flow import run_policy_database_guard
from app.orchestration.double_click_idempotency_flow import run_double_click_idempotency
from app.services.demo_seed_data import security_seed_examples
from app.schemas.contracts import (
    DoubleClickIdempotencyRequest,
    EnterpriseLeakRequest,
    PolicyDatabaseGuardRequest,
)


class NewGuardrailLabTests(unittest.TestCase):
    def test_enterprise_leak_blocks_secret(self) -> None:
        result = run_enterprise_data_leak_guard(
            EnterpriseLeakRequest(user_message="API_KEY=secret-value 를 사용해 줘.")
        )

        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["safe_to_send_llm"])
        self.assertIsNone(result["llm_context"])

    def test_enterprise_leak_masks_personal_information(self) -> None:
        result = run_enterprise_data_leak_guard(
            EnterpriseLeakRequest(user_message="kim@example.com, 010-1234-5678을 참고해 줘.")
        )
        self.assertEqual(result["action"], "mask")
        self.assertTrue(result["safe_to_send_llm"])
        self.assertIn("[MASKED_EMAIL]", result["llm_input"])
        self.assertIn("[MASKED_PHONE]", result["llm_input"])
        self.assertNotIn("kim@example.com", result["llm_input"])
        self.assertNotIn("010-1234-5678", result["llm_input"])
        self.assertEqual(result["llm_context"], {"user_message": result["llm_input"]})

    def test_policy_database_masks_email(self) -> None:
        result = run_policy_database_guard(
            PolicyDatabaseGuardRequest(user_message="담당자 kim@example.com 에게 안내해 줘.")
        )

        self.assertEqual(result["status"], "completed")
        self.assertIn("[MASKED_EMAIL]", result["output_text"])

    def test_seed_examples_are_available(self) -> None:
        seeds = security_seed_examples()

        self.assertIn("lab_11_enterprise_data_leak", seeds)
        self.assertIn("lab_12_policy_database", seeds)
        self.assertIn("lab_13_double_click_idempotency", seeds)

    def test_double_click_runs_save_once(self) -> None:
        calls = []

        def fake_claim(user_id, key, payload):
            calls.append((user_id, key, payload))
            return "claimed" if len(calls) == 1 else "reused"

        with patch("app.orchestration.double_click_idempotency_flow.claim_idempotency", side_effect=fake_claim), \
             patch("app.orchestration.double_click_idempotency_flow.save_itinerary", return_value={"itinerary_id": "demo"}) as save:
            result = run_double_click_idempotency(DoubleClickIdempotencyRequest())

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["save_count"], 1)
        save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
