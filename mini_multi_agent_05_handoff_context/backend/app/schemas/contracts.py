from typing import Literal
from pydantic import BaseModel, Field, model_validator


class HandoffEnvelope(BaseModel):
    handoff_id: str = Field(min_length=5)
    task_id: str
    trace_id: str
    from_agent: str
    to_agent: str
    responsibility: str = Field(min_length=5, max_length=300)
    context: dict[str, object]
    context_version: int = Field(default=1, ge=1)
    user_id: str
    hop_count: int = Field(default=1, ge=1, le=3)
    status: Literal["proposed", "validated", "accepted", "rejected", "transferred", "completed", "failed"] = "proposed"

    @model_validator(mode="after")
    def prevent_self_handoff(self):
        if self.from_agent == self.to_agent:
            raise ValueError("자기 자신에게 Handoff할 수 없습니다.")
        return self


class HandoffState(BaseModel):
    run_id: str
    task_id: str = "travel-001"
    owner_agent: str = "weather_agent"
    status: Literal["queued", "running", "completed", "failed", "rejected"] = "queued"
    handoff_status: str = "proposed"
    hop_count: int = Field(default=0, ge=0, le=3)
    processed_handoff_ids: list[str] = Field(default_factory=list)
    trace: list[dict[str, object]] = Field(default_factory=list)
    result: dict[str, object] | None = None
    error: str | None = None

    @model_validator(mode="after")
    def processed_ids_must_be_unique(self) -> "HandoffState":
        if len(self.processed_handoff_ids) != len(set(self.processed_handoff_ids)):
            raise ValueError("processed_handoff_ids에 중복 값이 있습니다.")
        return self


class WeatherHandoffContext(BaseModel):
    weather_cautions: list[str] = Field(default_factory=list)


class WeatherHandoffDecision(BaseModel):
    agent_id: Literal["weather_agent"] = "weather_agent"
    handoff_required: bool
    target_agent: Literal["itinerary_agent"] | None = None
    reason: str
    responsibility: str | None = None
    handoff_context: WeatherHandoffContext = Field(default_factory=WeatherHandoffContext)

    @model_validator(mode="after")
    def validate_decision(self) -> "WeatherHandoffDecision":
        if self.handoff_required:
            if self.target_agent is None:
                raise ValueError("Handoff 대상이 필요합니다.")
            if not self.responsibility:
                raise ValueError("이전할 책임 설명이 필요합니다.")
        elif self.target_agent or self.responsibility or self.handoff_context.weather_cautions:
            raise ValueError("Handoff가 없으면 대상, 책임과 Context가 비어 있어야 합니다.")
        return self


class ItineraryResult(BaseModel):
    agent_id: Literal["itinerary_agent"] = "itinerary_agent"
    destination: str
    day_plans: list[str] = Field(min_length=1, max_length=7)
    applied_constraints: list[str] = Field(default_factory=list, max_length=10)


class HandoffRunRequest(BaseModel):
    destination: str = Field(default="부산", min_length=1, max_length=50)
    days: int = Field(default=3, ge=1, le=7)
    user_id: str = Field(default="user-101", min_length=1, max_length=100)
    transport: str = Field(default="대중교통", min_length=1, max_length=100)


class RoutedSupportRequest(BaseModel):
    employee_id: str = Field(default="EMP-101", min_length=3, max_length=30)
    system_name: str = Field(default="사내 포털", min_length=1, max_length=100)
    issue: str = Field(min_length=3, max_length=300)


class RoutedSupportDecision(BaseModel):
    agent_id: Literal["support_router"] = "support_router"
    target_agent: Literal["account_support_agent", "device_support_agent", "access_support_agent"]
    reason: str = Field(min_length=1)
    responsibility: str = Field(min_length=5, max_length=300)


class DeviceSupportResult(BaseModel):
    agent_id: Literal["device_support_agent"] = "device_support_agent"
    summary: str = Field(min_length=1)
    next_steps: list[str] = Field(min_length=1, max_length=5)


class AccessSupportResult(BaseModel):
    agent_id: Literal["access_support_agent"] = "access_support_agent"
    summary: str = Field(min_length=1)
    next_steps: list[str] = Field(min_length=1, max_length=5)


class InternalHandoffDecision(BaseModel):
    agent_id: Literal["it_triage_agent"] = "it_triage_agent"
    handoff_required: bool
    target_agent: Literal["account_support_agent"] | None = None
    reason: str = Field(min_length=1)
    responsibility: str | None = None

    @model_validator(mode="after")
    def validate_decision(self) -> "InternalHandoffDecision":
        if self.handoff_required and (not self.target_agent or not self.responsibility):
            raise ValueError("Handoff 대상과 이전할 책임이 필요합니다.")
        if not self.handoff_required and (self.target_agent or self.responsibility):
            raise ValueError("Handoff가 없으면 대상과 책임이 비어 있어야 합니다.")
        return self


class AccountSupportResult(BaseModel):
    agent_id: Literal["account_support_agent"] = "account_support_agent"
    summary: str = Field(min_length=1)
    next_steps: list[str] = Field(min_length=1, max_length=5)


class RefundHandoffRequest(BaseModel):
    user_id: str = Field(default="customer-101", min_length=1, max_length=100)
    order_id: str = Field(default="ORDER-102", max_length=50)
    issue: str = Field(default="주문을 취소하고 환불받고 싶습니다.", min_length=3, max_length=300)


class RefundHandoffContext(BaseModel):
    order_id: str | None = None
    issue: str | None = None


class SupportRefundDecision(BaseModel):
    agent_id: Literal["customer_support_agent"] = "customer_support_agent"
    reason: str = Field(min_length=1)
    responsibility: str = Field(min_length=5)
    handoff_context: RefundHandoffContext = Field(default_factory=RefundHandoffContext)


class RefundHandoffResult(BaseModel):
    agent_id: Literal["refund_agent"] = "refund_agent"
    summary: str = Field(min_length=1)
    next_steps: list[str] = Field(min_length=1, max_length=5)


class InternalHandoffRequest(BaseModel):
    employee_id: str = Field(default="EMP-101", min_length=3, max_length=30)
    system_name: str = Field(default="사내 포털", min_length=1, max_length=100)
    issue: str = Field(default="로그인할 수 없습니다.", min_length=3, max_length=300)
