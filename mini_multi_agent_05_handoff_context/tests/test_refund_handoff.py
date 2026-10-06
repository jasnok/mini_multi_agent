import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.refund_handoff import run_refund_handoff  # noqa: E402
from app.schemas.contracts import (  # noqa: E402
    RefundHandoffResult, RefundHandoffRequest, RefundHandoffContext, SupportRefundDecision,
)


def proposal(order_id="ORDER-102", issue="주문을 취소하고 환불받고 싶습니다."):
    return SupportRefundDecision(
        reason="환불 문의", responsibility="환불 문의의 다음 확인 절차 안내",
        handoff_context=RefundHandoffContext(order_id=order_id, issue=issue),
    )


def refund_result():
    return RefundHandoffResult(summary="주문 상태를 확인하세요.", next_steps=["주문 상태 확인"])


class RefundHandoffTests(unittest.IsolatedAsyncioTestCase):
    @patch("app.orchestration.refund_handoff.run_agent", new_callable=AsyncMock)
    async def test_simple_handoff_transfers_after_result(self, agent):
        agent.side_effect = [(proposal(), {}, {}), (refund_result(), {}, {})]
        result = await run_refund_handoff(RefundHandoffRequest())
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["owner_agent"], "refund_agent")
        self.assertEqual(result["safe_context"], {"order_id": "ORDER-102", "issue": "주문을 취소하고 환불받고 싶습니다."})
        self.assertEqual(result["trace"][2]["data"]["context"], result["safe_context"])
        self.assertEqual(result["trace"][4]["owner_agent"], "customer_support_agent")
        self.assertEqual(result["trace"][5]["owner_agent"], "refund_agent")
        self.assertIn(result["trace"][4]["data"]["handoff_id"], agent.call_args_list[1].args[1])
        self.assertEqual(agent.call_args_list[1].args[2], RefundHandoffResult)

    @patch("app.orchestration.refund_handoff.run_agent", new_callable=AsyncMock)
    async def test_missing_order_id_is_blocked_before_refund_agent(self, agent):
        agent.return_value = (proposal(order_id=None), {}, {})
        result = await run_refund_handoff(RefundHandoffRequest(order_id=""))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["owner_agent"], "customer_support_agent")
        self.assertEqual(agent.await_count, 1)

    @patch("app.orchestration.refund_handoff.run_agent", new_callable=AsyncMock)
    async def test_changed_order_id_is_blocked_before_refund_agent(self, agent):
        agent.return_value = (proposal(order_id="ORDER-999"), {}, {})
        result = await run_refund_handoff(RefundHandoffRequest())
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["owner_agent"], "customer_support_agent")
        self.assertEqual(agent.await_count, 1)

    @patch("app.orchestration.refund_handoff.run_agent", new_callable=AsyncMock)
    async def test_original_issue_is_used_instead_of_llm_rewrite(self, agent):
        request = RefundHandoffRequest(issue="원래 고객의 환불 요청")
        agent.side_effect = [
            (proposal(issue="LLM이 다시 작성한 문의"), {}, {}),
            (refund_result(), {}, {}),
        ]

        result = await run_refund_handoff(request)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["safe_context"]["issue"], request.issue)
        self.assertIn(request.issue, agent.call_args_list[1].args[1])

    @patch("app.orchestration.refund_handoff.run_agent", new_callable=AsyncMock)
    async def test_target_failure_keeps_support_owner(self, agent):
        agent.side_effect = [(proposal(), {}, {}), RuntimeError("target unavailable")]
        result = await run_refund_handoff(RefundHandoffRequest())
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["owner_agent"], "customer_support_agent")
        self.assertIsNone(result["result"])



if __name__ == "__main__":
    unittest.main()
