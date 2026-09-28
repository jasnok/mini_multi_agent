import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.task_execution import execute_task  # noqa: E402
from app.schemas.contracts import TaskExecutionRequest  # noqa: E402


class TaskExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_input_stops_before_agent(self) -> None:
        request = TaskExecutionRequest(task_id="allocate_budget", inputs={"destination": "부산", "days": 3, "total_budget": 600_000})
        with patch("app.orchestration.task_execution.run_agent", new_callable=AsyncMock) as run:
            result = await execute_task(request)
        self.assertEqual(result["status"], "needs_information")
        self.assertEqual(result["missing_information"], ["people"])
        run.assert_not_awaited()

    async def test_validated_budget_completes_task(self) -> None:
        request = TaskExecutionRequest(task_id="allocate_budget", inputs={"destination": "부산", "days": 3, "people": 1, "total_budget": 600_000})
        agent_result = {"result": {"agent_id": "budget_agent", "currency": "KRW", "breakdown": {"transport": 60_000, "lodging": 220_000, "food": 150_000, "reserve": 170_000}, "total": 600_000}}
        with patch("app.orchestration.task_execution.run_agent", new_callable=AsyncMock, return_value=agent_result) as run:
            result = await execute_task(request)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["trace"][-1]["action"], "task_completed")
        run.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
