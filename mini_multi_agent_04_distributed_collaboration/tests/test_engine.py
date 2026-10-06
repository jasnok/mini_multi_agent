import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.agents.registry import AGENTS, validate_registry  # noqa: E402
from app.orchestration.engine import agent_result_contract, error_message, partial_policy, sanitize_handoff_context, tool_arguments  # noqa: E402
from app.schemas.contracts import CollaborationState  # noqa: E402


class EngineTests(unittest.TestCase):
    def test_agent_provider_mapping(self) -> None:
        expected = {"weather_agent": "openai", "place_agent": "ollama", "lodging_agent": "openai", "budget_agent": "openai", "support_agent": "openai", "refund_agent": "gemma", "itinerary_agent": "gemma", "event_content_agent": "openai", "event_promotion_agent": "ollama", "event_operation_agent": "openai", "event_plan_agent": "gemma"}
        self.assertEqual({key: AGENTS[key].provider for key in expected}, expected)

    def test_agent_result_contract_rejects_other_agent_id(self) -> None:
        contract = agent_result_contract("weather_agent")
        contract.model_validate({"agent_id": "weather_agent", "summary": "맑음"})
        with self.assertRaisesRegex(Exception, "weather_agent"):
            contract.model_validate({"agent_id": "place_agent", "summary": "맑음"})
        schema = contract.model_json_schema()
        self.assertEqual(schema["properties"]["agent_id"]["const"], "weather_agent")

    def test_mcp_task_group_exposes_underlying_error(self) -> None:
        error = ExceptionGroup("unhandled errors in a TaskGroup", [RuntimeError("get_weather: timed out")])
        self.assertEqual(error_message(error), "get_weather: timed out")

    def test_registry_is_valid(self) -> None:
        self.assertIsNone(validate_registry())

    def test_budget_arguments_come_from_request(self) -> None:
        value = tool_arguments("calculate_budget", "제주 2박 3일, 2명 여행")
        self.assertEqual(value, {"days": 3, "people": 2, "city": "제주"})

    def test_missing_people_does_not_use_hidden_default(self) -> None:
        self.assertIsNone(tool_arguments("calculate_budget", "부산 2박 3일 여행"))

    def test_order_id_comes_from_request(self) -> None:
        self.assertEqual(tool_arguments("get_order_status", "ORDER_777 배송 문의"), {"order_id": "ORDER-777"})

    def test_required_optional_blocks_required_failure(self) -> None:
        state = CollaborationState(status="partial_failure", results={"place_agent": {}}, failed_agents=["weather_agent", "budget_agent"])
        self.assertFalse(partial_policy(state, "required_optional")["can_continue"])

    def test_handoff_forbidden_context_is_blocked_before_filtering(self) -> None:
        with self.assertRaisesRegex(ValueError, "payment_token"):
            sanitize_handoff_context({"order_id": "ORDER-102", "payment_token": "secret-value"})

    def test_handoff_context_uses_allowlist(self) -> None:
        value = sanitize_handoff_context({"order_id": "ORDER-102", "issue": "배송 지연", "internal_note": "drop"})
        self.assertEqual(value, {"order_id": "ORDER-102", "issue": "배송 지연"})


if __name__ == "__main__": unittest.main()
