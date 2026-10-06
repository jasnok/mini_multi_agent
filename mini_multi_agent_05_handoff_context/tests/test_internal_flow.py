import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.internal_flow import run_internal_handoff  # noqa: E402
from app.schemas.contracts import (  # noqa: E402
    AccountSupportResult,
    InternalHandoffDecision,
    InternalHandoffRequest,
)


class InternalHandoffFlowTests(unittest.IsolatedAsyncioTestCase):
    @patch("app.orchestration.internal_flow.run_agent", new_callable=AsyncMock)
    async def test_owner_changes_after_target_result(self, run_agent: AsyncMock) -> None:
        run_agent.side_effect = [
            (InternalHandoffDecision(handoff_required=True, target_agent="account_support_agent", reason="계정 문제", responsibility="계정 확인 절차 안내"), {}, {}),
            (AccountSupportResult(summary="확인 절차", next_steps=["계정 상태 확인"]), {}, {}),
        ]

        result = await run_internal_handoff(InternalHandoffRequest())

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["owner_agent"], "account_support_agent")
        self.assertEqual(result["hop_count"], 1)
        self.assertEqual(run_agent.await_count, 2)
        self.assertEqual(set(result["safe_context"]), {"employee_id", "system_name", "issue"})

    @patch("app.orchestration.internal_flow.run_agent", new_callable=AsyncMock)
    async def test_rejected_handoff_keeps_original_owner(self, run_agent: AsyncMock) -> None:
        run_agent.return_value = (
            InternalHandoffDecision(handoff_required=False, reason="계정 지원 대상 아님"), {}, {}
        )

        result = await run_internal_handoff(InternalHandoffRequest())

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["owner_agent"], "it_triage_agent")
        self.assertEqual(run_agent.await_count, 1)

    @patch("app.orchestration.internal_flow.run_agent", new_callable=AsyncMock)
    async def test_triage_failure_returns_structured_failure(self, run_agent: AsyncMock) -> None:
        run_agent.side_effect = RuntimeError("provider unavailable")

        result = await run_internal_handoff(InternalHandoffRequest())

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["owner_agent"], "it_triage_agent")
        self.assertIn("provider unavailable", result["error"])
        self.assertIsNone(result["decision"])


if __name__ == "__main__":
    unittest.main()
