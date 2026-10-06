"""Lab 12: DB에서 읽은 것처럼 보안 정책을 적용한다."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.schemas.contracts import PolicyDatabaseGuardRequest


PolicyAction = Literal["block", "mask"]


@dataclass(frozen=True)
class SecurityPolicyRow:
    """운영 DB의 한 행(row)을 흉내 낸 수업용 데이터입니다."""

    policy_id: str
    category: str
    pattern: str
    action: PolicyAction
    enabled: bool = True


# 실제 DB 대신 리스트를 사용합니다.
# 수업에서는 이 목록이 PostgreSQL, Supabase, Redis, 사내 정책 DB에서 온다고 생각합니다.
POLICY_DATABASE = [
    SecurityPolicyRow("POL-001", "email", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "mask"),
    SecurityPolicyRow("POL-002", "phone", r"01[016789]-?\d{3,4}-?\d{4}", "mask"),
    SecurityPolicyRow("POL-003", "secret_key", r"(?:api_key|API_KEY|access_token|password)\s*=\s*[^\s]+", "block"),
    SecurityPolicyRow("POL-004", "internal_keyword", r"CONFIDENTIAL|INTERNAL_ONLY|프로젝트 코드명", "block"),
]


def load_enabled_policies() -> list[SecurityPolicyRow]:
    """DB 조회를 흉내 냅니다. 지금은 enabled=True인 정책만 돌려줍니다."""

    return [policy for policy in POLICY_DATABASE if policy.enabled]


def run_policy_database_guard(request: PolicyDatabaseGuardRequest) -> dict[str, object]:
    trace: list[dict[str, object]] = []
    output_text = request.user_message

    policies = load_enabled_policies()
    trace.append({
        "step": 1,
        "stage": "load_policy_database",
        "status": "completed",
        "message": f"활성 보안 정책 {len(policies)}개를 읽었습니다.",
    })

    for policy in policies:
        if not re.search(policy.pattern, output_text):
            continue

        if policy.action == "block":
            trace.append({
                "step": 2,
                "stage": "policy_guard",
                "status": "blocked",
                "message": f"{policy.policy_id} 정책에 의해 차단되었습니다.",
                "category": policy.category,
            })
            return {
                "status": "blocked",
                "blocked_at": "policy_guard",
                "action": "block",
                "output_text": None,
                "trace": trace,
            }

        output_text = re.sub(policy.pattern, f"[MASKED_{policy.category.upper()}]", output_text)
        trace.append({
            "step": 2,
            "stage": "policy_guard",
            "status": "masked",
            "message": f"{policy.policy_id} 정책에 따라 값을 마스킹했습니다.",
            "category": policy.category,
        })

    trace.append({
        "step": 3,
        "stage": "policy_result",
        "status": "allowed",
        "message": "정책 검사를 통과했습니다.",
    })
    return {
        "status": "completed",
        "blocked_at": None,
        "action": "mask" if output_text != request.user_message else "allow",
        "output_text": output_text,
        "trace": trace,
        "policies": [policy.__dict__ for policy in policies],
    }
