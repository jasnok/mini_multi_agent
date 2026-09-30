from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SupportRouteDecision(BaseModel):
    """Router가 반환하는 담당 Agent 선택 결과입니다.

    02에서 Agent 출력 계약을 검증한 것처럼 03에서는 Router의 선택도 계약으로 검증합니다.
    Literal을 사용하므로 목록에 없는 Agent 이름은 다음 단계로 전달되지 않습니다.
    """
    agent_id: Literal["router_agent"] = "router_agent"
    selected_agent: Literal["delivery_agent", "refund_agent", "technical_support_agent", "request_information"]
    reason: str = Field(min_length=1)
    missing_information: list[str] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def validate_information_state(self) -> "SupportRouteDecision":
        if self.selected_agent == "request_information" and not self.missing_information:
            raise ValueError("추가 정보 요청에는 missing_information이 필요합니다.")
        if self.selected_agent != "request_information" and self.missing_information:
            raise ValueError("Worker 선택 시 missing_information은 비어 있어야 합니다.")
        return self


class InternalRouteDecision(BaseModel):
    """사내 요청을 담당 Worker 하나로 연결하는 두 번째 Router 계약입니다."""

    agent_id: Literal["internal_router_agent"] = "internal_router_agent"
    selected_agent: Literal[
        "account_agent", "equipment_agent", "facility_agent", "request_information"
    ]
    reason: str = Field(min_length=1)
    missing_information: list[str] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def validate_information_state(self) -> "InternalRouteDecision":
        if self.selected_agent == "request_information" and not self.missing_information:
            raise ValueError("추가 정보 요청에는 missing_information이 필요합니다.")
        if self.selected_agent != "request_information" and self.missing_information:
            raise ValueError("Worker 선택 시 missing_information은 비어 있어야 합니다.")
        return self


class SupervisorDecision(BaseModel):
    """Supervisor가 현재 완료 상태를 보고 반환하는 다음 행동입니다.

    초보 과정에서는 next_agent만 먼저 확인합니다. context_keys는 참고하려는 이전 결과의
    이름이며, 03의 핵심 평가 대상은 아닙니다.
    """
    agent_id: Literal["supervisor_agent"] = "supervisor_agent"
    next_agent: Literal["analyst_agent", "developer_agent", "reviewer_agent", "finish"]
    instruction: str = Field(min_length=1)
    context_keys: list[str] = Field(default_factory=list, max_length=5)
    reason: str = Field(min_length=1)


class WorkerResult(BaseModel):
    agent_id: str
    summary: str
    details: list[str] = Field(default_factory=list, max_length=8)
    completed: bool = True


class IncidentSupervisorDecision(BaseModel):
    agent_id: Literal["incident_supervisor_agent"]
    next_agent: Literal["incident_analyst_agent", "incident_planner_agent", "incident_reviewer_agent", "finish"]
    reason: str = Field(min_length=1)


class IncidentAnalysisResult(BaseModel):
    agent_id: Literal["incident_analyst_agent"]
    symptoms: list[str] = Field(min_length=1)
    impact: list[str] = Field(min_length=1)
    information_to_verify: list[str] = Field(min_length=1)
    completion_criteria: list[str] = Field(min_length=1)


class IncidentPlanDraft(BaseModel):
    agent_id: Literal["incident_planner_agent"]
    actions: list[str] = Field(min_length=1)
    rollback_plan: str = Field(min_length=1)
    verification_steps: list[str] = Field(min_length=1)
    addressed_feedback: list[str]


class IncidentPlanResult(IncidentPlanDraft):
    revision: int = Field(ge=0)


class IncidentReviewDraft(BaseModel):
    agent_id: Literal["incident_reviewer_agent"]
    approved: bool
    feedback: list[str]
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def review_and_feedback_agree(self) -> "IncidentReviewDraft":
        if self.approved and self.feedback:
            raise ValueError("승인한 검토에는 수정 요청이 없어야 합니다.")
        if not self.approved and not self.feedback:
            raise ValueError("승인하지 않았다면 구체적인 feedback이 필요합니다.")
        return self


class IncidentReviewResult(IncidentReviewDraft):
    reviewed_revision: int = Field(ge=0)


class MessageRequest(BaseModel):
    message: str = Field(min_length=3, max_length=1000)


class IncidentPlanRequest(MessageRequest):
    """Lab 09 실행 요청입니다.

    demonstrate_revision은 교육 화면에서 첫 거절 → 수정 → 재검토 흐름을
    재현하기 위한 옵션입니다. 일반 실행처럼 Reviewer가 자유롭게 판단하게
    하려면 false로 보낼 수 있습니다.
    """

    demonstrate_revision: bool = True


class SupervisorRequest(MessageRequest):
    """Supervisor가 읽는 현재 상태입니다.

    completed_agents는 완료 순서, outputs는 완료된 Agent의 검증 결과입니다. 두 값이 서로
    다르면 다음 Agent를 안전하게 고를 수 없으므로 LLM 호출 전에 차단합니다.
    """
    completed_agents: list[str] = Field(default_factory=list)
    outputs: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_supervisor_state(self) -> "SupervisorRequest":
        plan = ["analyst_agent", "developer_agent", "reviewer_agent"]
        if self.completed_agents != plan[:len(self.completed_agents)]:
            raise ValueError("completed_agents는 analyst → developer → reviewer 순서의 완료 prefix여야 합니다.")
        if set(self.outputs) != set(self.completed_agents):
            raise ValueError("outputs에는 완료된 Agent의 결과만 정확히 포함해야 합니다.")
        return self


class RouterValidationRequest(BaseModel):
    payload: dict[str, object]
