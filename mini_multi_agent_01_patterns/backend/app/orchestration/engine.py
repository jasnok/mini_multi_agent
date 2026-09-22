from __future__ import annotations

import asyncio

from app.agents.registry import get_agent
from app.agents.runtime import run_agent
from app.providers.registry import generate_structured, model_for
from app.mcp.client import call_tool
from app.schemas.runs import AgentOutput, EvaluationDecision, HandoffDecision, RouteDecision, RunRequest, RunResult, SupervisorDecision, TraceEvent


class PatternEngine:
    def __init__(self, request: RunRequest, provider_override: str | None = None):
        self.request = request
        self.provider_override = provider_override
        self.result = RunResult(scenario=request.scenario, pattern=request.pattern, provider_mode=request.provider_mode, termination_reason="running")

    def provider_for(self, agent_id: str) -> str:
        if self.provider_override:
            return self.provider_override
        if self.request.provider_mode == "mixed":
            return self.request.provider_by_agent.get(agent_id, self.request.provider)
        return self.request.provider

    def trace(self, actor: str, action: str, status: str, metadata: dict[str, object] | None = None, **details: object) -> None:
        metadata = metadata or {}
        has_tool_metadata = metadata.get("tools") or metadata.get("skipped_tools")
        tool_details = {
            "tools": metadata.get("tools", []),
            "skipped_tools": metadata.get("skipped_tools", []),
            "tool_results": metadata.get("tool_results", {}),
        } if has_tool_metadata else {}
        self.result.trace.append(TraceEvent(step=len(self.result.trace) + 1, actor=actor, action=action, status=status, provider=metadata.get("provider_used"), model=metadata.get("model"), latency_ms=metadata.get("latency_ms"), details={**details, **tool_details}))

    async def agent(self, agent_id: str, context: object | None = None, provider_override: str | None = None) -> AgentOutput:
        provider = provider_override or self.provider_for(agent_id)
        self.trace(agent_id, "run", "started", {"provider_used": provider, "model": model_for(provider)})
        try:
            output, metadata = await run_agent(get_agent(agent_id), self.request.message, provider, context)
        except Exception as error:
            self.trace(agent_id, "run", "failed", {"provider_used": provider, "model": model_for(provider)}, error=f"{type(error).__name__}: {error}")
            raise
        self.result.selected_agents.append(agent_id)
        self.result.outputs[agent_id] = output.model_dump()
        self.trace(agent_id, "run", "completed", metadata)
        return output

    async def single_agent(self) -> None:
        output = await self.agent("travel_agent")
        self.result.summary = output.summary
        self.result.termination_reason = "single_agent_completed"

    async def independent(self) -> None:
        for agent_id in ("weather_agent", "place_agent", "budget_agent", "safety_agent"):
            await self.agent(agent_id)
        self.result.summary = "개별 결과만 존재하며 전체 일정으로 Join하지 않았습니다."
        self.result.termination_reason = "independent_agents_finished"

    async def orchestration_comparison(self) -> None:
        for agent_id in ("weather_agent", "budget_agent"):
            output = await self.agent(agent_id)
            self.result.outputs[f"independent:{agent_id}"] = output.model_dump()
        self.trace("orchestrator", "select_agents", "completed", selected=["weather_agent", "budget_agent"])
        joined = {}
        for agent_id in ("weather_agent", "budget_agent"):
            output = await self.agent(agent_id)
            joined[agent_id] = output.model_dump()
        self.result.summary = "독립 실행에는 전체 종료가 없고, 조정 실행에는 선택·수집·종료 Trace가 있습니다."
        self.result.outputs["orchestrated"] = joined
        self.result.termination_reason = "comparison_completed"

    async def sequential(self) -> None:
        context = None
        for agent_id in ("research_agent", "writer_agent", "reviewer_agent"):
            context = await self.agent(agent_id, context.model_dump() if context else None)
        self.result.summary = context.summary
        self.result.termination_reason = "sequential_pipeline_completed"

    async def parallel_join(self) -> None:
        ids = ("weather_agent", "place_agent", "budget_agent")
        outputs = await asyncio.gather(*(self.agent(agent_id) for agent_id in ids))
        joined = {item.agent_id: item.model_dump() for item in outputs}
        itinerary = await self.agent("itinerary_agent", joined)
        self.result.summary = itinerary.summary
        self.result.termination_reason = "parallel_results_joined"

    async def router(self) -> None:
        provider = self.provider_for("router")
        decision, metadata = await generate_structured(provider, f"고객지원 Router입니다. 배송은 delivery_agent, 환불 정책은 refund_policy_agent, 로그인·기술 문제는 technical_support_agent를 선택하세요. 요청: {self.request.message}", RouteDecision)
        self.trace("router", "select_agent", "completed", metadata, decision=decision.model_dump())
        output = await self.agent(decision.selected_agent)
        self.result.summary = output.summary
        self.result.termination_reason = "routed_agent_completed"

    async def supervisor_worker(self) -> None:
        completed: list[str] = []
        required_order = ["analyst_agent", "developer_agent", "reviewer_agent"]
        for _ in range(min(self.request.max_steps, len(required_order))):
            provider = self.provider_for("supervisor")
            expected = required_order[len(completed)]
            decision, metadata = await generate_structured(provider, f"코드 작업 Supervisor입니다. 완료 역할={completed}. 지금 선택할 수 있는 유일한 다음 역할은 {expected}입니다. next_agent={expected}로 선택하세요. 요청={self.request.message}", SupervisorDecision)
            self.trace("supervisor", "select_next", "completed", metadata, decision=decision.model_dump())
            if decision.next_agent != expected:
                self.trace("supervisor", "reject_invalid_selection", "blocked", metadata, selected=decision.next_agent, required=expected)
            await self.agent(expected, self.result.outputs)
            completed.append(expected)
        if completed != required_order:
            raise RuntimeError(f"최대 단계 안에 완료하지 못했습니다: {completed}")
        self.result.summary = self.result.outputs["reviewer_agent"]["summary"]
        self.result.termination_reason = "supervisor_finished"

    async def handoff(self) -> None:
        support = await self.agent("support_agent")
        provider = self.provider_for("support_agent")
        decision, metadata = await generate_structured(provider, f"Support Agent 결과를 보고 환불 정책 Agent에게 책임을 넘길지 판단하세요. 배송 지연 또는 환불 문의이면 target_agent는 refund_policy_agent입니다. 요청={self.request.message}, 결과={support.model_dump()}", HandoffDecision)
        self.trace("support_agent", "decide_handoff", "completed", metadata, decision=decision.model_dump())
        if not decision.handoff_required:
            self.result.summary = support.summary
            self.result.termination_reason = "handoff_not_required"
            return
        if decision.target_agent != "refund_policy_agent":
            raise RuntimeError("허용되지 않은 Handoff 대상입니다.")
        if not decision.context.order_id:
            raise RuntimeError("Handoff Context에 order_id가 없습니다.")
        handoff = {"from_agent": "support_agent", "to_agent": decision.target_agent, "responsibility": decision.reason, "context": decision.context.model_dump()}
        self.trace("orchestrator", "handoff", "completed", handoff=handoff)
        refund = await self.agent("refund_policy_agent", handoff)
        self.result.summary = refund.summary
        self.result.termination_reason = "handoff_accepted"

    async def evaluator_reviser(self) -> None:
        draft = await self.agent("writer_agent")
        requirements = await call_tool(
            "get_quality_requirements",
            {"scenario": "content"},
            frozenset({"get_quality_requirements"}),
        )
        self.trace("evaluator_agent", "load_requirements", "completed", details=requirements)
        for round_number in range(1, min(self.request.max_steps, 5) + 1):
            provider = self.provider_for("evaluator_agent")
            evaluation, metadata = await generate_structured(provider, f"다음 PostgreSQL 완료 조건을 기준으로 초안이 요청을 충족하고 안전한지 평가하세요. 완료 조건={requirements}, 초안={draft.summary}", EvaluationDecision)
            self.trace("evaluator_agent", "evaluate", "completed", metadata, round=round_number, evaluation=evaluation.model_dump())
            if evaluation.passed:
                self.result.summary = draft.summary
                self.result.termination_reason = "evaluation_passed"
                return
            if round_number == min(self.request.max_steps, 5):
                break
            draft = await self.agent("reviser_agent", {"draft": draft.model_dump(), "feedback": evaluation.feedback})
        raise RuntimeError("최대 수정 횟수 안에 평가를 통과하지 못했습니다.")

    async def provider_failover(self) -> None:
        attempts = []
        providers = (self.request.primary_provider, self.request.secondary_provider)
        for attempt_number, provider in enumerate(providers, start=1):
            try:
                if attempt_number == 1 and self.request.simulate_primary_failure:
                    raise RuntimeError("교육용 Primary 실패 시뮬레이션")
                output = await self.agent("writer_agent", provider_override=provider)
                attempts.append({"provider": provider, "model": model_for(provider), "status": "completed"})
                self.result.outputs["failover_attempts"] = attempts
                self.result.summary = output.summary
                self.result.termination_reason = "primary_completed" if attempt_number == 1 else "secondary_completed"
                self.trace("failover", "completed", "completed", {"provider_used": provider, "model": model_for(provider)}, failover_used=attempt_number > 1)
                return
            except Exception as error:
                attempts.append({"provider": provider, "model": model_for(provider), "status": "failed", "error": f"{type(error).__name__}: {error}"})
                self.trace("failover", "provider_attempt", "failed", {"provider_used": provider, "model": model_for(provider)}, attempt=attempt_number, error=str(error))
        self.result.outputs["failover_attempts"] = attempts
        raise RuntimeError("Primary와 Secondary 실제 LLM이 모두 실패했습니다.")

    async def run(self) -> RunResult:
        try:
            await getattr(self, self.request.pattern)()
        except Exception as error:
            self.result.status = "failed"
            self.result.termination_reason = "pattern_error"
            self.result.error = f"{type(error).__name__}: {error}"
            self.trace("orchestrator", "pattern_failed", "failed", error=self.result.error)
        return self.result
