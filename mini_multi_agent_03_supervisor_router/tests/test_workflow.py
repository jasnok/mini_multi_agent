import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.registry import AGENTS  # noqa: E402
from app.orchestration.engine import rule_router_agent, validate_route  # noqa: E402
from app.schemas.workflow import InternalRouteDecision, SupervisorRequest  # noqa: E402
from pydantic import ValidationError  # noqa: E402


class WorkflowTests(unittest.TestCase):
    def test_agent_provider_mapping(self) -> None:
        expected = {
            "router_agent": "openai", "supervisor_agent": "openai",
            "delivery_agent": "openai", "refund_agent": "gemma",
            "technical_support_agent": "ollama", "analyst_agent": "openai",
            "developer_agent": "ollama", "reviewer_agent": "gemma",
            "internal_router_agent": "openai", "account_agent": "openai",
            "equipment_agent": "ollama", "facility_agent": "gemma",
        }
        self.assertEqual({agent_id: AGENTS[agent_id].provider for agent_id in expected}, expected)

    def test_rule_router_selects_refund(self) -> None:
        self.assertEqual(rule_router_agent("주문을 환불하고 싶어요.").selected_agent, "refund_agent")

    def test_rule_router_uses_declared_priority_for_multi_intent_request(self) -> None:
        decision = rule_router_agent("ORDER-102 배송이 늦어서 환불하고 싶어요.")
        self.assertEqual(decision.selected_agent, "delivery_agent")

    def test_unknown_agent_is_rejected(self) -> None:
        result = validate_route({"selected_agent": "payment_agent", "reason": "결제"})
        self.assertFalse(result["valid"])

    def test_request_information_requires_missing_information(self) -> None:
        result = validate_route({"selected_agent": "request_information", "reason": "모호함"})
        self.assertFalse(result["valid"])

    def test_supervisor_state_requires_ordered_prefix(self) -> None:
        with self.assertRaises(ValidationError):
            SupervisorRequest(message="검증 기능을 구현해 주세요.", completed_agents=["reviewer_agent"], outputs={"reviewer_agent": {}})

    def test_supervisor_outputs_match_completed_agents(self) -> None:
        with self.assertRaises(ValidationError):
            SupervisorRequest(message="검증 기능을 구현해 주세요.", completed_agents=["analyst_agent"], outputs={})

    def test_internal_router_rejects_unknown_worker(self) -> None:
        with self.assertRaises(ValidationError):
            InternalRouteDecision(selected_agent="payment_agent", reason="결제 요청")

    def test_internal_router_requires_missing_information(self) -> None:
        with self.assertRaises(ValidationError):
            InternalRouteDecision(selected_agent="request_information", reason="요청이 모호함")



if __name__ == "__main__":
    unittest.main()
