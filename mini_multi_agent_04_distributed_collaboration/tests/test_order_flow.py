import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.order_flow import order_collaboration  # noqa: E402


def success(agent_id):
    return {"result": {"agent_id": agent_id, "summary": "교육용 모의 결과", "completed": True},
            "error": None, "provider": "test", "model": "test-model", "latency_ms": 1}


class OrderFlowTests(unittest.IsolatedAsyncioTestCase):
    @patch("app.orchestration.order_flow.agent", new_callable=AsyncMock)
    async def test_all_checks_allow_order_notice(self, agent):
        agent.side_effect = [success("inventory_check_agent"), success("payment_check_agent"),
                             success("coupon_guide_agent"), success("order_notice_agent")]
        result = await order_collaboration("ORDER-102 모의 주문")
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["join_guard"]["passed"])
        self.assertIn("order_notice_agent", result["results"])
        self.assertEqual(agent.await_count, 4)

    @patch("app.orchestration.order_flow.agent", new_callable=AsyncMock)
    async def test_inventory_failure_blocks_notice(self, agent):
        agent.side_effect = [success("payment_check_agent"), success("coupon_guide_agent")]
        result = await order_collaboration("ORDER-102 모의 주문", "inventory_check_agent")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["join_guard"]["missing_required"], ["inventory_check_agent"])
        self.assertNotIn("order_notice_agent", result["results"])
        self.assertEqual(agent.await_count, 2)

    @patch("app.orchestration.order_flow.agent", new_callable=AsyncMock)
    async def test_payment_failure_blocks_notice(self, agent):
        agent.side_effect = [success("inventory_check_agent"), success("coupon_guide_agent")]
        result = await order_collaboration("ORDER-102 모의 주문", "payment_check_agent")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["join_guard"]["missing_required"], ["payment_check_agent"])
        self.assertEqual(agent.await_count, 2)

    @patch("app.orchestration.order_flow.agent", new_callable=AsyncMock)
    async def test_optional_coupon_failure_still_allows_notice(self, agent):
        agent.side_effect = [success("inventory_check_agent"), success("payment_check_agent"),
                             success("order_notice_agent")]
        result = await order_collaboration("ORDER-102 모의 주문", "coupon_guide_agent")
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["join_guard"]["passed"])
        self.assertEqual(result["join_guard"]["optional_failed"], ["coupon_guide_agent"])
        self.assertEqual(agent.await_count, 3)

    @patch("app.orchestration.order_flow.agent", new_callable=AsyncMock)
    async def test_incomplete_payment_result_is_not_counted(self, agent):
        incomplete = success("payment_check_agent")
        incomplete["result"]["completed"] = False
        agent.side_effect = [success("inventory_check_agent"), incomplete, success("coupon_guide_agent")]
        result = await order_collaboration("ORDER-102 모의 주문")
        self.assertFalse(result["join_guard"]["passed"])
        self.assertEqual(agent.await_count, 3)


if __name__ == "__main__":
    unittest.main()
