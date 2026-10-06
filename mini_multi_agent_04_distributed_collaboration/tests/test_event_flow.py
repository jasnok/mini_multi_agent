import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.event_flow import event_collaboration  # noqa: E402


def success(agent_id: str) -> dict[str, object]:
    return {
        "result": {"agent_id": agent_id, "summary": f"{agent_id} 결과", "details": [], "completed": True},
        "error": None,
        "provider": "test",
        "model": "test-model",
        "latency_ms": 1,
    }


class EventFlowTests(unittest.IsolatedAsyncioTestCase):
    @patch("app.orchestration.event_flow.agent", new_callable=AsyncMock)
    async def test_three_workers_then_one_aggregator(self, mock_agent: AsyncMock) -> None:
        mock_agent.side_effect = [
            success("event_content_agent"),
            success("event_promotion_agent"),
            success("event_operation_agent"),
            success("event_plan_agent"),
        ]

        result = await event_collaboration("신입 개발자를 위한 온라인 행사를 준비해 주세요.")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(mock_agent.await_count, 4)
        self.assertIn("event_plan_agent", result["results"])

    @patch("app.orchestration.event_flow.agent", new_callable=AsyncMock)
    async def test_missing_required_result_blocks_join(self, mock_agent: AsyncMock) -> None:
        failed_content = {**success("event_content_agent"), "result": None, "error": "교육용 실패"}
        mock_agent.side_effect = [
            failed_content,
            success("event_promotion_agent"),
            success("event_operation_agent"),
        ]

        result = await event_collaboration("온라인 행사를 준비해 주세요.")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "required_result_missing")
        self.assertEqual(mock_agent.await_count, 3)


if __name__ == "__main__":
    unittest.main()
