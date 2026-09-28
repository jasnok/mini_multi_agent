import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.multi_task_message import execute_multi_task_from_message, extract_task_inputs  # noqa: E402
from app.schemas.contracts import MultiTaskMessageRequest  # noqa: E402


class MultiTaskMessageTests(unittest.IsolatedAsyncioTestCase):
    def test_extracts_three_task_inputs(self) -> None:
        values = extract_task_inputs("부산 2박 3일 여행, 2명, 대중교통, 예산 60만 원, 해산물 알레르기")
        self.assertEqual(values, {"destination": "부산", "days": 3, "people": 2, "transport": "대중교통", "constraints": ["해산물 알레르기"], "total_budget": 600000})

    async def test_missing_inputs_prevent_all_agent_calls(self) -> None:
        request = MultiTaskMessageRequest(message="부산 2박 3일 여행, 예산 60만 원")
        with patch("app.orchestration.multi_task_message.run_agent", new_callable=AsyncMock) as run:
            result = await execute_multi_task_from_message(request)
        self.assertEqual(result["status"], "needs_information")
        self.assertEqual(set(result["missing_information"]), {"people", "transport", "constraints"})
        run.assert_not_awaited()

    async def test_complete_request_runs_three_agents(self) -> None:
        request = MultiTaskMessageRequest(message="부산 2박 3일 여행, 2명, 대중교통, 예산 60만 원, 제약 없음")
        payloads = [
            {"result": {"agent_id": "weather_agent", "forecast_summary": "확인 필요", "cautions": [], "source_confirmed": True}},
            {"result": {"agent_id": "place_agent", "places": ["해운대"], "selection_reason": "대중교통 접근 가능"}},
            {"result": {"agent_id": "budget_agent", "currency": "KRW", "breakdown": {"transport": 60000, "lodging": 220000, "food": 150000, "reserve": 170000}, "total": 600000}},
        ]
        with patch("app.orchestration.multi_task_message.run_agent", new_callable=AsyncMock, side_effect=payloads) as run:
            result = await execute_multi_task_from_message(request)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(run.await_count, 3)


if __name__ == "__main__":
    unittest.main()
