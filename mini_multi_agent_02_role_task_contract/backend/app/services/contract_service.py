from pydantic import ValidationError

from app.schemas.contracts import VALIDATION_CONTRACTS, ValidationRequest


VALIDATION_CASES = {
    "normal_budget": {"contract_name": "BudgetResult", "payload": {"breakdown": {"transport": 60000, "lodging": 220000, "food": 150000, "reserve": 170000}, "total": 600000}},
    "missing_field": {"contract_name": "WeatherResult", "payload": {"agent_id": "weather_agent", "cautions": []}},
    "wrong_role": {"contract_name": "WeatherResult", "payload": {"agent_id": "budget_agent", "forecast_summary": "맑음", "source_confirmed": True}},
    "total_mismatch": {"contract_name": "BudgetResult", "payload": {"breakdown": {"transport": 60000, "lodging": 220000, "food": 150000, "reserve": 170000}, "total": 550000}},
    "negative_budget": {"contract_name": "BudgetResult", "payload": {"breakdown": {"transport": -10000, "lodging": 220000, "food": 150000, "reserve": 240000}, "total": 600000}},
}


def validate_contract(request: ValidationRequest) -> dict[str, object]:
    """선택한 계약으로 Payload를 검증하고 화면이 읽기 쉬운 결과를 반환합니다."""
    schema = VALIDATION_CONTRACTS[request.contract_name]
    try:
        result = schema.model_validate(request.payload)
        return {"valid": True, "contract": request.contract_name, "result": result.model_dump(), "errors": []}
    except ValidationError as error:
        errors = [{"location": list(item["loc"]), "message": item["msg"], "type": item["type"]} for item in error.errors()]
        return {"valid": False, "contract": request.contract_name, "result": None, "errors": errors}


def contract_schemas() -> dict[str, object]:
    """Contract Explorer가 입력·출력 계약을 모두 보여 주도록 JSON Schema를 반환합니다."""
    return {name: schema.model_json_schema() for name, schema in VALIDATION_CONTRACTS.items()}
