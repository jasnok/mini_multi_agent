from app.agents.registry import load_policies
from app.agents.input_guard_agent import normalize_policy_text


def response_strings(value: object):
    """사용자에게 반환될 객체에서 모든 문자열 값을 재귀적으로 찾습니다."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from response_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from response_strings(child)


def inspect_response(response_text: str) -> tuple[bool, str]:
    policy = load_policies()["response"]
    normalized = normalize_policy_text(response_text)
    for phrase in policy["blocked_claims"]:
        if normalize_policy_text(phrase) in normalized:
            return False, f"실행하지 않은 작업을 주장합니다: {phrase}"
    for pattern in policy["sensitive_patterns"]:
        if normalize_policy_text(pattern) in normalized:
            return False, f"민감정보 패턴이 포함되었습니다: {pattern}"
    return True, "응답 Policy를 통과했습니다."


def inspect_response_payload(payload: object) -> tuple[bool, str]:
    """최종 answer뿐 아니라 함께 반환되는 초안·근거 필드도 검사합니다."""
    for text in response_strings(payload):
        allowed, reason = inspect_response(text)
        if not allowed:
            return False, reason
    return True, "전체 응답 Payload가 Response Policy를 통과했습니다."
