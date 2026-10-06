from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def new_run_id() -> str:
    return f"run-{uuid4().hex[:12]}"


class AgentResult(BaseModel):
    agent_id: str
    summary: str
    details: list[str] = Field(default_factory=list, max_length=8)
    completed: bool = True


class PlanStep(BaseModel):
    """Execution Plan의 한 단계입니다.

    agents는 이 단계에서 실행할 Agent, depends_on은 먼저 끝나야 하는 단계입니다.
    """
    step_id: str
    agents: list[str] = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    join: bool = False


class ExecutionPlan(BaseModel):
    """여러 PlanStep을 실행 순서대로 모은 전체 실행 계획입니다."""
    goal: str
    steps: list[PlanStep] = Field(min_length=1)
    max_steps: int = Field(default=6, ge=1, le=12)

    @model_validator(mode="after")
    def validate_dependencies(self) -> "ExecutionPlan":
        known = set()
        for step in self.steps:
            missing = set(step.depends_on) - known
            if missing:
                raise ValueError(f"먼저 정의되지 않은 의존 단계: {sorted(missing)}")
            if step.step_id in known:
                raise ValueError(f"중복 step_id: {step.step_id}")
            known.add(step.step_id)
        return self


class TraceEvent(BaseModel):
    step: int
    actor: str
    action: str
    status: Literal["started", "completed", "failed", "blocked", "skipped"]
    provider: str | None = None
    model: str | None = None
    latency_ms: float | None = None
    details: dict[str, object] = Field(default_factory=dict)


class CollaborationState(BaseModel):
    """실행 중 Orchestrator가 기록하는 현재 상태입니다.

    Worker가 직접 수정하지 않고 Orchestrator가 완료 결과와 실패를 한곳에 기록합니다.
    """
    run_id: str = Field(default_factory=new_run_id)
    task_id: str = "travel-001"
    status: Literal["planned", "running", "completed", "failed", "partial_failure"] = "planned"
    current_step: str | None = None
    results: dict[str, object] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)
    completed_agents: list[str] = Field(default_factory=list)
    failed_agents: list[str] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)


class HandoffContext(BaseModel):
    order_id: str | None = None
    issue: str | None = None
    delivery_issue: str | None = None


class HandoffDecision(BaseModel):
    agent_id: Literal["support_agent"] = "support_agent"
    handoff_required: bool
    target_agent: Literal["refund_agent", "delivery_agent"] | None = None
    reason: str
    direct_answer: str | None = None
    responsibility: str | None = None
    handoff_context: HandoffContext = Field(default_factory=HandoffContext)

class RunRequest(BaseModel):
    message: str = Field(min_length=3, max_length=1000)
    fail_agent: Literal["weather_agent", "place_agent", "budget_agent"] | None = None
    policy: Literal["fail_fast", "best_effort", "required_optional"] = "required_optional"


class OrderRunRequest(BaseModel):
    message: str = Field(default="ORDER-102 상품 1개 주문 확인을 도와주세요.", min_length=3, max_length=1000)
    fail_agent: Literal["inventory_check_agent", "payment_check_agent", "coupon_guide_agent"] | None = None


class PlanValidationRequest(BaseModel):
    plan: dict[str, object]


class TravelDecisionRequest(BaseModel):
    message: str = Field(min_length=3, max_length=1000)
    budget_limit: int = Field(default=650_000, ge=0)
    rain_threshold: int = Field(default=50, ge=0, le=100)
    rain_probability_override: int | None = Field(default=None, ge=0, le=100)
