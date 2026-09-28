import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.weather_place_lodging_budget import execute_weather_place_lodging_budget
from app.schemas.contracts import MultiTaskMessageRequest


REQUEST = MultiTaskMessageRequest(message="부산 2박 3일 여행, 1명, 대중교통, 예산 60만 원, 제약 없음")


def weather(rain):
    return {"result": {"agent_id": "weather_agent", "forecast_summary": "예보", "cautions": [], "source_confirmed": True},
            "tool_results": {"get_weather": {"success": True, "current": {"precipitation": 0},
                                             "daily": {"precipitation_probability_max": [50 if rain else 10]}}}}


PLACE_ITEMS = [
    {"name": "부산박물관", "indoor": True, "category": "문화"},
    {"name": "해운대해수욕장", "indoor": False, "category": "자연"},
]


def place(name):
    return {"result": {"agent_id": "place_agent", "places": [name], "selection_reason": "조건에 맞음"},
            "tool_results": {"search_places": {"success": True, "items": PLACE_ITEMS}}}


def lodging():
    return {"result": {"agent_id": "lodging_agent", "selected_option": "잠정 숙소", "selection_reason": "비용 기준",
                       "nightly_cost": 110000, "nights": 2, "total_cost": 220000, "availability_confirmed": False},
            "tool_results": {"get_lodging_reference": {"success": True, "option": "잠정 숙소",
                                                       "nightly_cost": 110000, "nights": 2, "total_cost": 220000}}}


def budget():
    return {"result": {"agent_id": "budget_agent", "currency": "KRW", "breakdown": {
        "transport": 60000, "lodging": 220000, "food": 150000, "reserve": 170000}, "total": 600000}}


class VerifiedFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_rain_requires_indoor_then_runs_lodging_and_budget(self):
        with patch("app.orchestration.weather_place_lodging_budget.run_agent", new_callable=AsyncMock,
                   side_effect=[weather(True), place("부산박물관"), lodging(), budget()]) as run:
            result = await execute_weather_place_lodging_budget(REQUEST)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(run.await_count, 4)
        self.assertTrue(run.await_args_list[1].kwargs["context"]["indoor_only"])
        self.assertEqual(run.await_args_list[2].kwargs["context"]["place_result"]["places"], ["부산박물관"])
        self.assertEqual(run.await_args_list[3].kwargs["context"]["lodging_result"]["total_cost"], 220000)

    async def test_rain_rejects_outdoor_and_skips_following_tasks(self):
        with patch("app.orchestration.weather_place_lodging_budget.run_agent", new_callable=AsyncMock,
                   side_effect=[weather(True), place("해운대해수욕장")]) as run:
            result = await execute_weather_place_lodging_budget(REQUEST)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(run.await_count, 2)
        self.assertEqual([item["status"] for item in result["results"]],
                         ["completed", "failed", "skipped", "skipped"])

    async def test_lodging_tool_mismatch_prevents_budget(self):
        bad_lodging = lodging()
        bad_lodging["result"]["nightly_cost"] = 90000
        bad_lodging["result"]["total_cost"] = 180000
        with patch("app.orchestration.weather_place_lodging_budget.run_agent", new_callable=AsyncMock,
                   side_effect=[weather(False), place("해운대해수욕장"), bad_lodging]) as run:
            result = await execute_weather_place_lodging_budget(REQUEST)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(run.await_count, 3)
        self.assertEqual(result["results"][3]["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
