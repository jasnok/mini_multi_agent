import sys
import unittest
from pathlib import Path

from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas.contracts import BudgetAgentInput, BudgetResult, SupportCaseResult, ValidationRequest  # noqa: E402
from app.services.contract_service import validate_contract  # noqa: E402


class ContractTests(unittest.TestCase):
    def test_support_case_requires_order_id_when_completed(self) -> None:
        with self.assertRaises(ValidationError):
            SupportCaseResult.model_validate({
                "issue": "배송 지연",
                "requested_action": "확인 방법 안내",
                "completed": True,
                "missing_information": [],
            })

    def test_incomplete_support_case_lists_missing_information(self) -> None:
        result = SupportCaseResult.model_validate({
            "order_id": None,
            "issue": "배송 지연",
            "requested_action": "확인 방법 안내",
            "completed": False,
            "missing_information": ["order_id"],
        })
        self.assertFalse(result.completed)

    def test_budget_agent_input_is_valid(self) -> None:
        request = BudgetAgentInput.model_validate({
            "destination": "부산",
            "days": 3,
            "total_budget": 600_000,
        })
        self.assertEqual(request.days, 3)

    def test_zero_days_are_rejected_before_agent_execution(self) -> None:
        with self.assertRaises(ValidationError):
            BudgetAgentInput.model_validate({
                "destination": "부산",
                "days": 0,
                "total_budget": 600_000,
            })

    def test_budget_total_must_equal_breakdown(self) -> None:
        with self.assertRaises(ValidationError):
            BudgetResult.model_validate({
                "breakdown": {"transport": 60_000, "lodging": 220_000, "food": 150_000, "reserve": 170_000},
                "total": 550_000,
            })

    def test_place_result_can_be_validated_through_api_contract(self) -> None:
        request = ValidationRequest(contract_name="PlaceResult", payload={
            "agent_id": "place_agent",
            "places": ["감천문화마을"],
            "selection_reason": "대중교통으로 접근할 수 있습니다.",
        })
        self.assertTrue(validate_contract(request)["valid"])

    def test_wrong_agent_role_is_rejected(self) -> None:
        request = ValidationRequest(contract_name="WeatherResult", payload={
            "agent_id": "budget_agent",
            "forecast_summary": "맑음",
            "source_confirmed": True,
        })
        self.assertFalse(validate_contract(request)["valid"])


if __name__ == "__main__":
    unittest.main()
