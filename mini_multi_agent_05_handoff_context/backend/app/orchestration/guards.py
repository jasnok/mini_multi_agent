from app.agents.registry import get_route
from app.schemas.contracts import HandoffEnvelope, HandoffState

FORBIDDEN_KEYS = {"api_key", "password", "secret", "raw_messages", "payment_token", "internal_prompt"}


def find_forbidden_paths(value: object, path: str = "context") -> list[str]:
    """중첩된 dict/list 안에서도 금지된 Context Key의 경로를 찾습니다."""
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in FORBIDDEN_KEYS:
                found.append(child_path)
            found.extend(find_forbidden_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_forbidden_paths(child, f"{path}[{index}]"))
    return found

def validate_handoff(handoff: HandoffEnvelope, state: HandoffState, expected_user_id: str):
    if handoff.status != "proposed":
        raise ValueError("proposed 상태의 Handoff만 검증할 수 있습니다.")
    if handoff.user_id != expected_user_id:
        raise PermissionError("다른 사용자의 Handoff입니다.")
    if handoff.task_id != state.task_id:
        raise PermissionError("현재 작업과 다른 task_id의 Handoff입니다.")
    if handoff.trace_id != state.run_id:
        raise PermissionError("현재 실행과 다른 trace_id의 Handoff입니다.")
    if state.owner_agent != handoff.from_agent:
        raise PermissionError("현재 책임자만 Handoff를 제안할 수 있습니다.")
    if handoff.handoff_id in state.processed_handoff_ids:
        raise ValueError("이미 처리한 Handoff입니다.")
    route = get_route(handoff.from_agent, handoff.to_agent)
    allowed = set(route["required_context"] + route["optional_context"])
    missing = set(route["required_context"]) - set(handoff.context)
    empty_required = sorted(
        key for key in route["required_context"]
        if key in handoff.context and handoff.context[key] in (None, "", [], {})
    )
    exposed = find_forbidden_paths(handoff.context)
    unknown = set(handoff.context) - allowed
    expected_hop = state.hop_count + 1
    if handoff.hop_count != expected_hop:
        raise PermissionError(
            f"Handoff hop_count가 연속되지 않습니다: expected={expected_hop}, actual={handoff.hop_count}"
        )
    if handoff.hop_count > route["max_hops"]:
        raise PermissionError("최대 Handoff 횟수를 초과했습니다.")
    if missing: raise ValueError(f"필수 Context 누락: {sorted(missing)}")
    if empty_required: raise ValueError(f"필수 Context 값이 비어 있습니다: {empty_required}")
    if exposed: raise ValueError(f"민감 Context 차단: {sorted(exposed)}")
    if unknown: raise ValueError(f"허용되지 않은 Context: {sorted(unknown)}")
    return handoff.model_copy(update={"status": "validated"})
