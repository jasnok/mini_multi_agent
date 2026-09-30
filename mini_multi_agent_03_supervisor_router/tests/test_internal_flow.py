import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.internal_flow import run_internal_router_flow  # noqa: E402
from app.schemas.workflow import MessageRequest  # noqa: E402


class InternalRouterFlowTests(unittest.IsolatedAsyncioTestCase):
    @patch("app.orchestration.internal_flow.safe_agent", new_callable=AsyncMock)
    async def test_selected_worker_runs_once(self, safe_agent: AsyncMock) -> None:
        safe_agent.side_effect = [
            {"status": "completed", "result": {"agent_id": "internal_router_agent", "selected_agent": "equipment_agent", "reason": "노트북 문제", "missing_information": []}},
            {"status": "completed", "result": {"agent_id": "equipment_agent", "summary": "점검 순서", "details": [], "completed": True}},
        ]

        result = await run_internal_router_flow(MessageRequest(message="노트북 화면이 켜지지 않습니다."))

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["worker"]["result"]["agent_id"], "equipment_agent")
        self.assertEqual(safe_agent.await_count, 2)

    @patch("app.orchestration.internal_flow.safe_agent", new_callable=AsyncMock)
    async def test_missing_information_does_not_run_worker(self, safe_agent: AsyncMock) -> None:
        safe_agent.return_value = {
            "status": "completed",
            "result": {"agent_id": "internal_router_agent", "selected_agent": "request_information", "reason": "분류 정보 부족", "missing_information": ["계정·장비·시설 중 어떤 요청인지"]},
        }

        result = await run_internal_router_flow(MessageRequest(message="도움이 필요합니다."))

        self.assertEqual(result["status"], "needs_information")
        self.assertIsNone(result["worker"])
        self.assertEqual(safe_agent.await_count, 1)


if __name__ == "__main__":
    unittest.main()
