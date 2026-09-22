from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


ProviderName = Literal["openai", "gemini", "ollama", "gemma"]
PatternName = Literal["single_agent", "independent", "orchestration_comparison", "sequential", "parallel_join", "router", "supervisor_worker", "handoff", "evaluator_reviser", "provider_failover"]
ProviderMode = Literal["single", "compare", "mixed"]


class RunRequest(BaseModel):
    scenario: Literal["travel", "support", "content", "code"] = "travel"
    pattern: PatternName = "parallel_join"
    provider_mode: ProviderMode = "single"
    provider: ProviderName = "openai"
    provider_by_agent: dict[str, ProviderName] = Field(default_factory=dict)
    message: str = Field(min_length=3, max_length=1000)
    max_steps: int = Field(default=6, ge=1, le=12)
    primary_provider: ProviderName = "gemma"
    secondary_provider: ProviderName = "openai"
    simulate_primary_failure: bool = False


class AgentOutput(BaseModel):
    agent_id: str
    summary: str
    recommendations: list[str] = Field(default_factory=list, max_length=8)
    completed: bool = True


class RouteDecision(BaseModel):
    selected_agent: Literal["delivery_agent", "refund_policy_agent", "technical_support_agent"]
    reason: str


class SupervisorDecision(BaseModel):
    next_agent: Literal["analyst_agent", "developer_agent", "reviewer_agent", "finish"]
    reason: str


class EvaluationDecision(BaseModel):
    passed: bool
    feedback: str
    missing_requirements: list[str] = Field(default_factory=list)


class HandoffContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str
    status: str | None = None


class HandoffDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handoff_required: bool
    target_agent: Literal["refund_policy_agent"] | None = None
    reason: str
    context: HandoffContext


class TraceEvent(BaseModel):
    step: int
    actor: str
    action: str
    status: Literal["started", "completed", "failed", "blocked"]
    provider: str | None = None
    model: str | None = None
    latency_ms: float | None = None
    details: dict[str, object] = Field(default_factory=dict)


class RunResult(BaseModel):
    run_id: str = Field(default_factory=lambda: f"run-{uuid4().hex[:12]}")
    scenario: str
    pattern: str
    provider_mode: str
    status: Literal["completed", "failed", "blocked"] = "completed"
    selected_agents: list[str] = Field(default_factory=list)
    outputs: dict[str, object] = Field(default_factory=dict)
    summary: str | None = None
    termination_reason: str
    trace: list[TraceEvent] = Field(default_factory=list)
    error: str | None = None
