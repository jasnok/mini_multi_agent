import re

from app.agents.registry import load_policies


def normalize_policy_text(value: str) -> str:
    """공백·구두점 삽입으로 차단 문구를 우회하지 못하게 비교용 문자열을 만든다."""
    return re.sub(r"[\W_]+", "", value.casefold())


def inspect_input(user_message: str) -> tuple[bool, str]:
    policy = load_policies()["input"]
    if len(user_message) > policy["max_length"]:
        return False, f"입력은 {policy['max_length']}자를 넘을 수 없습니다."
    normalized = normalize_policy_text(user_message)
    for phrase in policy["blocked_phrases"]:
        if normalize_policy_text(phrase) in normalized:
            return False, f"Prompt Injection 의심 문구가 발견되었습니다: {phrase}"
    return True, "입력 Policy를 통과했습니다."


def inspect_input_fields(fields: dict[str, object]) -> tuple[bool, str]:
    """LLM Prompt에 들어갈 모든 사용자 문자열을 필드별로 검사합니다."""
    for field, value in fields.items():
        values = value if isinstance(value, list) else [value]
        for item in values:
            if not isinstance(item, str):
                continue
            allowed, reason = inspect_input(item)
            if not allowed:
                return False, f"{field}: {reason}"
    return True, "모든 사용자 입력 필드가 Input Policy를 통과했습니다."
