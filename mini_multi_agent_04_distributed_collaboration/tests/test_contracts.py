import sys
import unittest
from pathlib import Path
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.schemas.contracts import ExecutionPlan, HandoffDecision  # noqa: E402
from openai.lib._pydantic import to_strict_json_schema


class ContractTests(unittest.TestCase):
    def test_handoff_schema_is_strict_for_openai(self) -> None:
        schema = to_strict_json_schema(HandoffDecision)
        context = schema["$defs"]["HandoffContext"]
        self.assertEqual(context["additionalProperties"], False)
        self.assertEqual(set(context["required"]), set(context["properties"]))

    def test_handoff_without_context_is_valid(self) -> None:
        decision = HandoffDecision.model_validate({
            "handoff_required": False, "reason": "환불 문의가 아닙니다.",
            "handoff_context": {"order_id": None, "issue": None},
        })
        self.assertFalse(decision.handoff_required)

    def test_forward_dependency_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ExecutionPlan.model_validate({"goal": "test", "steps": [{"step_id": "join", "agents": ["itinerary_agent"], "depends_on": ["research"]}, {"step_id": "research", "agents": ["weather_agent"]}]})

    def test_duplicate_step_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ExecutionPlan.model_validate({"goal": "test", "steps": [{"step_id": "same", "agents": ["weather_agent"]}, {"step_id": "same", "agents": ["budget_agent"]}]})


if __name__ == "__main__": unittest.main()
