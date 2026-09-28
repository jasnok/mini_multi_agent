import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.support_flow import run_support_flow  # noqa: E402
from app.schemas.contracts import MultiLlmRequest  # noqa: E402


def agent_result(agent_id: str, result: dict | None) -> dict:
    return {
        "status": "completed" if result else "failed",
        "agent_id": agent_id,
        "result": result,
        "error": None if result else "test failure",
    }


class SupportFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_verified_analysis_is_passed_to_writer(self) -> None:
        analyst = agent_result("support_analyst_agent", {
            "agent_id": "support_analyst_agent",
            "order_id": "ORDER-102",
            "issue": "배송 지연",
            "requested_action": "확인 방법 안내",
            "completed": True,
            "missing_information": [],
        })
        writer = agent_result("support_writer_agent", {
            "agent_id": "support_writer_agent",
            "message": "주문번호로 배송 상태를 확인해 주세요.",
            "next_actions": ["주문 조회 메뉴 확인"],
            "used_order_id": "ORDER-102",
        })
        mocked = AsyncMock(side_effect=[analyst, writer])
        with patch("app.orchestration.support_flow.run_agent", mocked):
            result = await run_support_flow(MultiLlmRequest(message="ORDER-102 배송이 늦습니다."))

        self.assertEqual(result["status"], "completed")
        self.assertEqual(mocked.await_count, 2)
        self.assertEqual(mocked.await_args_list[1].args[2]["order_id"], "ORDER-102")

    async def test_missing_order_id_skips_writer(self) -> None:
        analyst = agent_result("support_analyst_agent", {
            "agent_id": "support_analyst_agent",
            "order_id": None,
            "issue": "배송 지연",
            "requested_action": "확인 방법 안내",
            "completed": False,
            "missing_information": ["order_id"],
        })
        mocked = AsyncMock(return_value=analyst)
        with patch("app.orchestration.support_flow.run_agent", mocked):
            result = await run_support_flow(MultiLlmRequest(message="상품이 아직 오지 않았습니다."))

        self.assertEqual(result["status"], "needs_information")
        self.assertIsNone(result["response"])
        self.assertEqual(mocked.await_count, 1)
        self.assertEqual(result["trace"][-1]["action"], "skipped")


if __name__ == "__main__":
    unittest.main()
