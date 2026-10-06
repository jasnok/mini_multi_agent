import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.registry import get_agent  # noqa: E402
from app.orchestration.engine import handoff, sanitize_handoff_context  # noqa: E402
from app.schemas.contracts import HandoffContext, HandoffDecision  # noqa: E402


class DynamicHandoffTests(unittest.IsolatedAsyncioTestCase):
    async def test_refund_question_selects_refund_context(self):
        decision = HandoffDecision(handoff_required=True, target_agent="refund_agent",
            reason="환불 조건 문의", responsibility="환불 조건 안내",
            handoff_context=HandoffContext(order_id="ORDER-102", issue="환불 조건 확인"))
        response = {"result": {"agent_id": "refund_agent", "summary": "환불 조건 안내"}, "error": None}
        with patch("app.orchestration.engine.generate", new_callable=AsyncMock) as generate, \
             patch("app.orchestration.engine.agent", new_callable=AsyncMock) as target:
            generate.return_value = (decision, {"provider": "openai"})
            target.return_value = response
            result = await handoff("ORDER-102 환불 조건을 알고 싶습니다.")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["selected_route"], "refund_agent")
        self.assertEqual(result["owner_agent"], "refund_agent")
        self.assertEqual(result["handoff"]["context"], {"order_id": "ORDER-102", "issue": "환불 조건 확인"})
        target.assert_awaited_once_with("refund_agent", "ORDER-102 환불 조건을 알고 싶습니다.", result["safe_context"])

    async def test_delivery_question_selects_delivery_context(self):
        decision = HandoffDecision(handoff_required=True, target_agent="delivery_agent",
            reason="배송 문의", responsibility="배송 확인 방법 안내",
            handoff_context=HandoffContext(order_id="ORDER-102", delivery_issue="배송 지연"))
        with patch("app.orchestration.engine.generate", new_callable=AsyncMock) as generate, \
             patch("app.orchestration.engine.agent", new_callable=AsyncMock) as target:
            generate.return_value = (decision, {"provider": "openai"})
            target.return_value = {"result": {"agent_id": "delivery_agent", "summary": "배송 확인 방법"}, "error": None}
            result = await handoff("ORDER-102 배송이 늦습니다.")
        self.assertEqual(result["selected_route"], "delivery_agent")
        self.assertEqual(result["owner_agent"], "delivery_agent")
        self.assertEqual(result["handoff"]["context"], {"order_id": "ORDER-102", "delivery_issue": "배송 지연"})
        self.assertEqual(get_agent("delivery_agent").allowed_tools, frozenset())

    async def test_general_question_is_answered_without_handoff(self):
        decision = HandoffDecision(handoff_required=False, reason="일반 문의",
                                   direct_answer="고객센터 안내 페이지에서 확인하세요.")
        with patch("app.orchestration.engine.generate", new_callable=AsyncMock) as generate, \
             patch("app.orchestration.engine.agent", new_callable=AsyncMock) as target:
            generate.return_value = (decision, {"provider": "openai"})
            result = await handoff("고객센터 운영시간은 어디서 확인하나요?")
        self.assertEqual(result["selected_route"], "direct_answer")
        self.assertIsNone(result["handoff"])
        self.assertEqual(result["owner_agent"], "support_agent")
        self.assertEqual(result["answer"], "고객센터 안내 페이지에서 확인하세요.")
        target.assert_not_awaited()

    async def test_general_answer_ignores_unused_context(self):
        decision = HandoffDecision(handoff_required=False, reason="일반 문의",
            direct_answer="고객센터 안내 페이지에서 확인하세요.",
            handoff_context=HandoffContext(issue="전달하지 않을 내용"))
        with patch("app.orchestration.engine.generate", new_callable=AsyncMock) as generate, \
             patch("app.orchestration.engine.agent", new_callable=AsyncMock) as target:
            generate.return_value = (decision, {})
            result = await handoff("고객센터 운영시간은 어디서 확인하나요?")
        self.assertEqual(result["selected_route"], "direct_answer")
        self.assertIsNone(result["safe_context"])
        target.assert_not_awaited()

    async def test_missing_context_blocks_target_call(self):
        decision = HandoffDecision(handoff_required=True, target_agent="delivery_agent",
            reason="배송 문의", handoff_context=HandoffContext(order_id="ORDER-102"))
        with patch("app.orchestration.engine.generate", new_callable=AsyncMock) as generate, \
             patch("app.orchestration.engine.agent", new_callable=AsyncMock) as target:
            generate.return_value = (decision, {})
            result = await handoff("ORDER-102 배송 지연")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["owner_agent"], "support_agent")
        target.assert_not_awaited()

    async def test_order_id_mismatch_blocks_target_call(self):
        decision = HandoffDecision(handoff_required=True, target_agent="refund_agent",
            reason="환불 문의", handoff_context=HandoffContext(order_id="ORDER-999", issue="환불"))
        with patch("app.orchestration.engine.generate", new_callable=AsyncMock) as generate, \
             patch("app.orchestration.engine.agent", new_callable=AsyncMock) as target:
            generate.return_value = (decision, {})
            result = await handoff("ORDER-102 환불 문의")
        self.assertEqual(result["status"], "blocked")
        target.assert_not_awaited()

    def test_delivery_allowlist(self):
        self.assertEqual(sanitize_handoff_context({"order_id": "ORDER-102", "issue": "drop", "delivery_issue": "지연"}, "delivery_agent"),
                         {"order_id": "ORDER-102", "delivery_issue": "지연"})


if __name__ == "__main__": unittest.main()
