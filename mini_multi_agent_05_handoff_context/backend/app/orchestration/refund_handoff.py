"""Lab 09: simple contract → envelope → guard → target result."""
from uuid import uuid4

from app.agents.registry import get_agent
from app.agents.runtime import run_agent
from app.orchestration.guards import validate_handoff
from app.schemas.contracts import (
    HandoffEnvelope, HandoffState, RefundHandoffResult,
    RefundHandoffRequest, SupportRefundDecision,
)


async def run_refund_handoff(request: RefundHandoffRequest) -> dict[str, object]:
    state = HandoffState(run_id=f"run-{uuid4().hex[:12]}", task_id="refund-inquiry-001",
                         owner_agent="customer_support_agent", status="running")
    decision = None
    proposed_context = None

    def record(title, status, message, data=None):
        state.trace.append({"title": title, "status": status, "message": message,
                            "data": data, "owner_agent": state.owner_agent})

    def response():
        return {**state.model_dump(), "decision": decision.model_dump() if decision else None,
                "safe_context": proposed_context}

    record("1 · 고객 문의 접수", "received", "상담 Agent가 환불 문의를 받았습니다.", request.model_dump())
    try:
        support = get_agent("customer_support_agent")
        decision, _, _ = await run_agent(
            support,
            f"당신은 customer_support_agent입니다. Goal: {support.goal}\nInstructions: {support.instructions}\n"
            f"고객 요청: {request.model_dump_json()}\nSupportRefundDecision 계약으로 인계할 책임과 Context를 반환하세요.",
            SupportRefundDecision,
        )
        record("2 · 상담 결과 · SupportRefundDecision", "completed", decision.reason, decision.model_dump())
        proposed = decision.handoff_context.model_dump()
        if proposed.get("order_id") != request.order_id:
            raise ValueError("상담 Agent가 원래 요청과 다른 주문번호를 제안했습니다.")
        # 문의 내용은 LLM이 요약하거나 바꾼 문장 대신 검증된 원본 요청을 전달한다.
        proposed_context = {"order_id": request.order_id, "issue": request.issue}
        handoff = HandoffEnvelope(
            handoff_id=f"handoff-{state.run_id}", task_id=state.task_id, trace_id=state.run_id,
            from_agent="customer_support_agent", to_agent="refund_agent",
            responsibility=decision.responsibility, context=proposed_context, user_id=request.user_id,
        )
        record("3 · 상담 결과로 HandoffEnvelope 생성", "proposed", handoff.responsibility, handoff.model_dump())
        try:
            checked = validate_handoff(handoff, state, request.user_id)
        except Exception as error:
            record("4 · Guard 점검", "failed", str(error))
            raise
        state.handoff_status = checked.status
        record("4 · Guard 점검", "validated",
               "주문번호·문의 내용과 인계 경로를 확인했습니다.",
               {"required_context": ["order_id", "issue"], "checked_context_keys": list(checked.context)})
        record("5 · 환불 Agent에 전달", "validated", "검증된 Envelope를 환불 Agent에게 전달합니다.",
               checked.model_dump())
        refund = get_agent("refund_agent")
        result, _, _ = await run_agent(
            refund,
            f"당신은 refund_agent입니다. Goal: {refund.goal}\nInstructions: {refund.instructions}\n"
            f"검증된 Handoff: {checked.model_dump_json()}\nRefundHandoffResult 계약으로 다음 확인 절차를 반환하세요.",
            RefundHandoffResult,
        )
        state.result = result.model_dump()
        state.owner_agent = "refund_agent"
        state.hop_count = checked.hop_count
        state.processed_handoff_ids.append(checked.handoff_id)
        state.handoff_status = "completed"
        state.status = "completed"
        record("6 · 환불 Agent 결과와 책임 이전", "completed", "환불 Agent가 결과를 반환하여 이 Handoff 작업의 책임이 이전되었습니다.", state.result)
    except Exception as error:
        state.status = "failed"
        state.handoff_status = "failed"
        state.error = f"{type(error).__name__}: {error}"
        record("실행 실패", "failed", state.error)
    return response()
