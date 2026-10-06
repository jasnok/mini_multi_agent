import sys
import unittest
from pathlib import Path
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.agents.registry import AGENTS, validate_registry  # noqa: E402
from app.orchestration.guards import validate_handoff  # noqa: E402
from app.schemas.contracts import HandoffEnvelope, HandoffState  # noqa: E402


def envelope(**changes):
    values = {
        "handoff_id": "handoff-001", "task_id": "travel-001", "trace_id": "run-001",
        "from_agent": "weather_agent", "to_agent": "itinerary_agent",
        "responsibility": "날씨를 반영한 일정을 작성한다.", "user_id": "user-101",
        "context": {"destination": "부산", "days": 3, "weather_summary": {"forecast": "rain"}},
    }
    values.update(changes)
    return HandoffEnvelope(**values)


class HandoffTests(unittest.TestCase):
    def test_weather_handoff_contract_is_openai_strict(self) -> None:
        from openai.lib._pydantic import to_strict_json_schema
        from app.schemas.contracts import WeatherHandoffDecision

        schema = to_strict_json_schema(WeatherHandoffDecision)
        context = schema["$defs"]["WeatherHandoffContext"]
        self.assertEqual(context["additionalProperties"], False)
        self.assertEqual(set(context["required"]), set(context["properties"]))

    def test_agent_provider_mapping(self) -> None:
        self.assertEqual({key: value.provider for key, value in AGENTS.items()}, {"weather_agent": "openai", "itinerary_agent": "gemma", "it_triage_agent": "openai", "account_support_agent": "gemma", "support_router": "openai", "device_support_agent": "gemma", "access_support_agent": "gemma", "customer_support_agent": "openai", "refund_agent": "gemma"})

    def test_registry_is_valid(self) -> None:
        self.assertIsNone(validate_registry())

    def test_valid_handoff_becomes_validated(self) -> None:
        checked = validate_handoff(envelope(), HandoffState(run_id="run-001"), "user-101")
        self.assertEqual(checked.status, "validated")

    def test_non_proposed_handoff_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "proposed"):
            validate_handoff(envelope(status="validated"), HandoffState(run_id="run-001"), "user-101")

    def test_empty_required_context_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "비어"):
            validate_handoff(envelope(context={"destination": "", "days": 3, "weather_summary": {}}), HandoffState(run_id="run-001"), "user-101")

    def test_sensitive_context_is_rejected(self) -> None:
        context = {"destination": "부산", "days": 3, "weather_summary": {"forecast": "rain"}, "api_key": "secret"}
        with self.assertRaisesRegex(ValueError, "민감 Context"):
            validate_handoff(envelope(context=context), HandoffState(run_id="run-001"), "user-101")

    def test_nested_sensitive_context_is_rejected(self) -> None:
        context = {
            "destination": "부산", "days": 3,
            "weather_summary": {"forecast": "rain", "metadata": {"api_key": "secret"}},
        }
        with self.assertRaisesRegex(ValueError, r"context\.weather_summary\.metadata\.api_key"):
            validate_handoff(envelope(context=context), HandoffState(run_id="run-001"), "user-101")

    def test_task_and_trace_must_match_current_state(self) -> None:
        state = HandoffState(run_id="run-001", task_id="travel-001")
        with self.assertRaisesRegex(PermissionError, "task_id"):
            validate_handoff(envelope(task_id="other-task"), state, "user-101")
        with self.assertRaisesRegex(PermissionError, "trace_id"):
            validate_handoff(envelope(trace_id="other-run"), state, "user-101")

    def test_hop_count_must_follow_state(self) -> None:
        state = HandoffState(run_id="run-001", hop_count=1)
        with self.assertRaisesRegex(PermissionError, "hop_count"):
            validate_handoff(envelope(hop_count=1), state, "user-101")

    def test_processed_handoff_ids_are_unique(self) -> None:
        with self.assertRaises(ValidationError):
            HandoffState(run_id="run-001", processed_handoff_ids=["handoff-001", "handoff-001"])

    def test_internal_handoff_route_accepts_minimum_context(self) -> None:
        internal = HandoffEnvelope(
            handoff_id="handoff-internal-001", task_id="internal-it-001", trace_id="run-001",
            from_agent="it_triage_agent", to_agent="account_support_agent",
            responsibility="계정 문제의 확인 절차를 안내한다.", user_id="EMP-101",
            context={"employee_id": "EMP-101", "system_name": "사내 포털", "issue": "로그인 오류"},
        )
        state = HandoffState(run_id="run-001", task_id="internal-it-001", owner_agent="it_triage_agent")
        self.assertEqual(validate_handoff(internal, state, "EMP-101").status, "validated")


if __name__ == "__main__": unittest.main()
