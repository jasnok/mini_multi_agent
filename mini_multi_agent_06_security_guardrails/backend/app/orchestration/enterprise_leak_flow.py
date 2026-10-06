"""Lab 11: 회사 기밀과 개인정보가 외부 AI로 나가기 전에 검사한다."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.contracts import EnterpriseLeakRequest


@dataclass(frozen=True)
class LeakRule:
    name: str
    description: str
    pattern: re.Pattern[str]
    action: str


# 초보자용 예제라서 규칙을 한눈에 볼 수 있게 코드 가까이에 둡니다.
# 운영 환경에서는 이 규칙을 DB나 사내 보안 정책 저장소에서 읽어올 수 있습니다.
LEAK_RULES = [
    LeakRule("email", "고객 이메일", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "mask"),
    LeakRule("phone", "휴대폰 번호", re.compile(r"01[016789]-?\d{3,4}-?\d{4}"), "mask"),
    LeakRule("secret", "API Key 또는 Token", re.compile(r"(?:api_key|API_KEY|access_token|password)\s*=\s*[^\s]+"), "block"),
    LeakRule("internal", "회사 내부 전용 문구", re.compile(r"CONFIDENTIAL|INTERNAL_ONLY|프로젝트 코드명|운영자 전용"), "block"),
]


def run_enterprise_data_leak_guard(request: EnterpriseLeakRequest) -> dict[str, object]:
    """직원 입력을 외부 LLM에 보내기 전에 차단 또는 마스킹합니다."""

    trace: list[dict[str, object]] = []
    output_text = request.user_message

    trace.append({
        "step": 1,
        "stage": "employee_input",
        "status": "received",
        "message": "직원이 사내 AI 서비스에 문장을 입력했습니다.",
    })

    for rule in LEAK_RULES:
        if not rule.pattern.search(output_text):
            continue

        if rule.action == "block":
            trace.append({
                "step": 2,
                "stage": "data_leak_guard",
                "status": "blocked",
                "message": f"{rule.description}이 감지되어 외부 LLM 호출을 중단했습니다.",
                "rule": rule.name,
            })
            return {
                "status": "blocked",
                "action": "block",
                "blocked_at": "data_leak_guard",
                "safe_to_send_llm": False,
                "original_text": request.user_message,
                "llm_input": None,
                "llm_context": None,
                "trace": trace,
            }

        output_text = rule.pattern.sub(f"[MASKED_{rule.name.upper()}]", output_text)
        trace.append({
            "step": 2,
            "stage": "data_leak_guard",
            "status": "masked",
            "message": f"{rule.description}을 마스킹했습니다.",
            "rule": rule.name,
        })

    trace.append({
        "step": 3,
        "stage": "llm_boundary",
        "status": "allowed",
        "message": "민감한 값이 없거나 마스킹되어 외부 LLM에 전달할 수 있습니다.",
    })
    return {
        "status": "completed",
        "action": "mask" if output_text != request.user_message else "allow",
        "blocked_at": None,
        "safe_to_send_llm": True,
        "original_text": request.user_message,
        "llm_input": output_text,
        "llm_context": {"user_message": output_text},
        "trace": trace,
    }
