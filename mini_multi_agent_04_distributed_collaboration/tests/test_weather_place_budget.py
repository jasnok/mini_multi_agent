import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.orchestration.weather_place_budget_graph import choose_place, run_weather_place_budget  # noqa: E402


PLACES = [
    {"name": "미술관", "is_indoor": True, "estimated_cost": 10000},
    {"name": "해변", "is_indoor": False, "estimated_cost": 0},
]


def agent_responses(probability):
    async def fake_agent(agent_id, message, context=None):
        response = {"result": {"agent_id": agent_id, "summary": "완료"}, "error": None}
        if agent_id == "weather_agent":
            response["tool_context"] = {"get_weather": {
                "success": True, "forecast": {"precipitation_probability_max": [10, probability, 20]},
            }}
        elif agent_id == "place_agent":
            response["tool_context"] = {"search_places": {"success": True, "places": PLACES}}
        else:
            response["tool_context"] = {"calculate_budget": {"success": True, "total": 600000}}
        return response

    return fake_agent


class WeatherPlaceBudgetTests(unittest.IsolatedAsyncioTestCase):
    def test_old_mcp_place_response_explains_restart(self):
        response = {"tool_context": {"search_places": {"success": True, "places": [{"name": "미술관"}]}}}
        with self.assertRaisesRegex(ValueError, "MCP 서버를 최신 코드로 재시작"):
            choose_place(response, indoor=True)

    async def test_rain_selects_indoor_and_adds_place_cost(self):
        with patch("app.orchestration.weather_place_budget_graph.agent", side_effect=agent_responses(70)):
            result = await run_weather_place_budget("부산 2박 3일, 1명", 650000)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["weather_risk"], "rain")
        self.assertEqual(result["selected_place"]["name"], "미술관")
        self.assertEqual(result["budget"]["estimated_total"], 610000)
        self.assertEqual([item["actor"] for item in result["trace"]],
                         ["weather_agent", "weather_guard", "indoor_place", "budget_agent"])

    async def test_dry_selects_outdoor(self):
        with patch("app.orchestration.weather_place_budget_graph.agent", side_effect=agent_responses(30)):
            result = await run_weather_place_budget("부산 2박 3일, 1명", 650000)
        self.assertEqual(result["weather_risk"], "dry")
        self.assertEqual(result["selected_place"]["name"], "해변")
        self.assertEqual(result["budget"]["estimated_total"], 600000)

    async def test_budget_limit_is_reported(self):
        with patch("app.orchestration.weather_place_budget_graph.agent", side_effect=agent_responses(70)):
            result = await run_weather_place_budget("부산 2박 3일, 1명", 600000)
        self.assertEqual(result["status"], "over_budget")
        self.assertEqual(result["budget"]["remaining"], -10000)

    async def test_explicit_probability_uses_manual_graph_branch(self):
        calls = []

        async def fake_agent(agent_id, message, context=None):
            calls.append(agent_id)
            if agent_id == "weather_agent":
                raise AssertionError("입력 모드에서는 날씨 Tool을 호출하면 안 됩니다.")
            if agent_id == "place_agent":
                return {"result": {"agent_id": agent_id}, "error": None,
                        "tool_context": {"search_places": {"success": True, "places": PLACES}}}
            return {"result": {"agent_id": agent_id}, "error": None,
                    "tool_context": {"calculate_budget": {"success": True, "total": 600000}}}

        with patch("app.orchestration.weather_place_budget_graph.agent", side_effect=fake_agent):
            result = await run_weather_place_budget("부산 2박 3일, 1명", 650000, 50, 70)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["weather_source"], "user_input")
        self.assertEqual(result["selected_place"]["name"], "미술관")
        self.assertNotIn("weather_agent", calls)
        self.assertEqual(result["trace"][0]["actor"], "weather_input")

    async def test_missing_input_stops_before_agents(self):
        with patch("app.orchestration.weather_place_budget_graph.agent") as mock_agent:
            result = await run_weather_place_budget("부산 여행", 650000)
        self.assertEqual(result["status"], "needs_information")
        mock_agent.assert_not_called()
