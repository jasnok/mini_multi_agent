import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.task_execution import execute_task_from_message, extract_budget_inputs  # noqa: E402
from app.schemas.contracts import TaskMessageRequest  # noqa: E402


class TaskMessageTests(unittest.IsolatedAsyncioTestCase):
    def test_extracts_budget_inputs_from_request(self) -> None:
        self.assertEqual(
            extract_budget_inputs("부산 2박 3일 여행, 1명, 예산 60만 원"),
            {"destination": "부산", "days": 3, "people": 1, "total_budget": 600_000},
        )

    async def test_missing_people_asks_without_running_agent(self) -> None:
        request = TaskMessageRequest(task_id="allocate_budget", message="부산 2박 3일 여행, 예산 60만 원")
        with patch("app.orchestration.task_execution.run_agent", new_callable=AsyncMock) as run:
            result = await execute_task_from_message(request)
        self.assertEqual(result["status"], "needs_information")
        self.assertEqual(result["missing_information"], ["people"])
        self.assertIn("몇 명", result["question"])
        run.assert_not_awaited()

    async def test_follow_up_merges_answer_and_runs_agent(self) -> None:
        request = TaskMessageRequest(
            task_id="allocate_budget",
            message="2명",
            known_inputs={"destination": "부산", "days": 3, "total_budget": 600_000},
        )
        agent_result = {"result": {"agent_id": "budget_agent", "currency": "KRW", "breakdown": {"transport": 60_000, "lodging": 220_000, "food": 150_000, "reserve": 170_000}, "total": 600_000}}
        with patch("app.orchestration.task_execution.run_agent", new_callable=AsyncMock, return_value=agent_result) as run:
            result = await execute_task_from_message(request)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["collected_inputs"]["people"], 2)
        run.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
