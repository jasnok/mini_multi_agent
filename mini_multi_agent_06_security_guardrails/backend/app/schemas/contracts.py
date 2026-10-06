from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GuardrailRunRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=50)
    destination: str = Field(min_length=1, max_length=50)
    days: int = Field(ge=1, le=7)
    preferences: list[str] = Field(default_factory=list, max_length=5)
    user_message: str = Field(min_length=1, max_length=500)

    @field_validator("user_id", "destination", "user_message")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("공백만 입력할 수 없습니다.")
        return value.strip()

    @field_validator("preferences")
    @classmethod
    def validate_preferences(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("빈 취향 값은 허용되지 않습니다.")
        if any(len(value) > 50 for value in cleaned):
            raise ValueError("취향 값은 각각 50자를 넘을 수 없습니다.")
        return cleaned


class TravelDraft(BaseModel):
    title: str
    summary: str
    daily_plan: list[str] = Field(min_length=1, max_length=7)
    safety_note: str


class FinalAnswer(BaseModel):
    answer: str
    used_facts: list[str]


class AuditEvent(BaseModel):
    sequence: int
    stage: str
    agent_id: str
    status: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class SupportSecurityRequest(BaseModel):
    customer_id: str = Field(default="CUST-101", min_length=3, max_length=50)
    issue: str = Field(default="로그인할 수 없습니다.", min_length=3, max_length=300)
    user_message: str = Field(default="로그인 문제의 확인 방법을 알려 주세요.", min_length=1, max_length=500)

    @field_validator("customer_id", "issue", "user_message")
    @classmethod
    def support_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("공백만 입력할 수 없습니다.")
        return value.strip()


class SupportDraft(BaseModel):
    summary: str
    checks: list[str] = Field(min_length=1, max_length=5)


class SupportFinalAnswer(BaseModel):
    answer: str
    used_facts: list[str] = Field(default_factory=list, max_length=5)


class EnterpriseLeakRequest(BaseModel):
    """회사 내부 AI 서비스에 직원이 입력한 문장을 검사하는 요청입니다."""

    employee_id: str = Field(default="EMP-101", min_length=3, max_length=50)
    user_message: str = Field(default="부산 출장 일정을 정리해 줘.", min_length=1, max_length=500)

    @field_validator("employee_id", "user_message")
    @classmethod
    def enterprise_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("공백만 입력할 수 없습니다.")
        return value.strip()


class PolicyDatabaseGuardRequest(BaseModel):
    """DB나 정책 저장소에서 읽은 보안 규칙으로 문장을 검사하는 요청입니다."""

    user_message: str = Field(default="담당자에게 출장 일정을 안내해 줘.", min_length=1, max_length=500)

    @field_validator("user_message")
    @classmethod
    def policy_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("공백만 입력할 수 없습니다.")
        return value.strip()


class DoubleClickIdempotencyRequest(BaseModel):
    """사용자가 저장 버튼을 두 번 클릭한 상황을 재현하는 요청입니다."""

    user_id: str = Field(default="user-101", min_length=1, max_length=50)
    itinerary_title: str = Field(default="부산 2박 3일 일정", min_length=1, max_length=100)
    idempotency_key: str = Field(default="double-click-save-v1", min_length=1, max_length=100)

    @field_validator("user_id", "itinerary_title", "idempotency_key")
    @classmethod
    def double_click_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("공백만 입력할 수 없습니다.")
        return value.strip()


class ApprovalRunRequest(BaseModel):
    """승인 대기형 여행 Workflow의 최초 요청입니다."""

    user_id: str = Field(min_length=1, max_length=50)
    destination: str = Field(min_length=1, max_length=50)
    days: int = Field(ge=1, le=7)
    preferences: list[str] = Field(default_factory=list, max_length=5)
    user_message: str = Field(min_length=1, max_length=500)
    weather_scenario: Literal["rain", "clear"] = "rain"

    @field_validator("user_id", "destination", "user_message")
    @classmethod
    def approval_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("공백만 입력할 수 없습니다.")
        return value.strip()


class ApprovalDecisionRequest(BaseModel):
    """대기 중인 변경 작업에 대한 사용자의 결정입니다."""

    approval_id: str = Field(min_length=5, max_length=100)
    idempotency_key: str = Field(min_length=1, max_length=100)
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=300)
    hotel_id: str | None = Field(default=None, max_length=50)

    @field_validator("approval_id", "idempotency_key")
    @classmethod
    def decision_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("공백만 입력할 수 없습니다.")
        return value.strip()
