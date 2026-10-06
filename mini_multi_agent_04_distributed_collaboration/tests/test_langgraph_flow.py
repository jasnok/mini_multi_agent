import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.orchestration.langgraph_flow import run_langgraph_travel  # noqa: E402


class LangGraphFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_agents_run_in_order_with_accumulated_context(self) -> None:
        calls = []

        async def fake_agent(agent_id, message, context=None):
            calls.append((agent_id, context))
            return {"result": {"agent_id": agent_id, "summary": "완료"}, "error": None}

        with patch("app.orchestration.langgraph_flow.agent", side_effect=fake_agent):
            result = await run_langgraph_travel("부산 2박 3일, 1명")

        self.assertEqual(result["status"], "completed")
        self.assertEqual([agent_id for agent_id, _ in calls], [
            "weather_agent", "place_agent", "lodging_agent", "budget_agent", "itinerary_agent"
        ])
        self.assertIsNone(calls[0][1])
        self.assertEqual(set(calls[1][1]), {"weather_agent"})
        self.assertEqual(set(calls[2][1]), {"weather_agent", "place_agent"})
        self.assertEqual(set(calls[3][1]), {"weather_agent", "place_agent", "lodging_agent"})
        self.assertEqual(set(calls[4][1]), {"weather_agent", "place_agent", "lodging_agent", "budget_agent"})

    async def test_failure_stops_later_agents(self) -> None:
        calls = []

        async def fake_agent(agent_id, message, context=None):
            calls.append(agent_id)
            if agent_id == "place_agent":
                return {"result": None, "error": "장소 조회 실패"}
            return {"result": {"agent_id": agent_id, "summary": "완료"}, "error": None}

        with patch("app.orchestration.langgraph_flow.agent", side_effect=fake_agent):
            result = await run_langgraph_travel("부산 2박 3일, 1명")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_agents"], ["place_agent"])
        self.assertEqual(calls, ["weather_agent", "place_agent"])
        self.assertEqual(result["trace"][-1]["action"], "agent_failed")
