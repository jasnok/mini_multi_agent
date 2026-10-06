"""Lab 07: 같은 Handoff 구조를 사내 IT 계정 요청에 적용한다."""

from uuid import uuid4

from app.agents.registry import get_agent
from app.agents.runtime import run_agent
from app.orchestration.guards import validate_handoff
from app.schemas.contracts import (
    AccountSupportResult,
    HandoffEnvelope,
    HandoffState,
    InternalHandoffDecision,
    InternalHandoffRequest,
)


async def run_internal_handoff(request: InternalHandoffRequest) -> dict[str, object]:
    """접수 Agent가 계정 지원 Agent에게 책임과 최소 Context를 넘깁니다."""
    run_id = f"run-{uuid4().hex[:12]}"
    state = HandoffState(
        run_id=run_id,
        task_id="internal-it-001",
        owner_agent="it_triage_agent",
        status="running",
    )
    def record(title, status, message, data=None):
        state.trace.append({"title": title, "status": status, "message": message,
                            "data": data, "owner_agent": state.owner_agent})

    record("1 · 사내 IT 요청 접수", "received", "IT 접수 Agent가 요청을 받았습니다.", {
        "employee_id": request.employee_id, "system_name": request.system_name,
        "issue": request.issue,
    })

    triage_profile = get_agent("it_triage_agent")
    triage_prompt = f"""당신은 it_triage_agent입니다.
직원 ID: {request.employee_id}
시스템: {request.system_name}
문제: {request.issue}
계정 지원이 필요하면 account_support_agent에게 넘길 책임을 정하세요.
InternalHandoffDecision 계약으로 반환하세요."""
    try:
        decision, _, _ = await run_agent(
            triage_profile, triage_prompt, InternalHandoffDecision
        )
    except Exception as error:
        state.status = "failed"
        state.handoff_status = "failed"
        state.error = f"{type(error).__name__}: {error}"
        record("2 · IT 접수 Agent 판단", "failed", state.error)
        return {**state.model_dump(), "decision": None, "safe_context": None}
    record("2 · IT 접수 Agent 판단", "completed", decision.reason, decision.model_dump())
    if not decision.handoff_required:
        state.status = "rejected"
        state.handoff_status = "rejected"
        record("3 · 인계하지 않음", "rejected", decision.reason)
        return {**state.model_dump(), "decision": decision.model_dump(), "safe_context": None}

    safe_context = {
        "employee_id": request.employee_id,
        "system_name": request.system_name,
        "issue": request.issue,
    }
    handoff = HandoffEnvelope(
        handoff_id=f"handoff-{run_id}",
        task_id=state.task_id,
        trace_id=run_id,
        from_agent="it_triage_agent",
        to_agent="account_support_agent",
        responsibility=decision.responsibility or "계정 문제의 다음 확인 절차를 안내한다.",
        context=safe_context,
        user_id=request.employee_id,
    )
    record("3 · 인계 제안: it_triage_agent → account_support_agent", "proposed",
           handoff.responsibility, handoff.model_dump())
    try:
        checked = validate_handoff(handoff, state, request.employee_id)
    except Exception as error:
        state.status = "failed"
        state.handoff_status = "failed"
        state.error = f"{type(error).__name__}: {error}"
        record("4 · Guard 점검", "failed", state.error)
        return {**state.model_dump(), "decision": decision.model_dump(), "safe_context": safe_context}
    state.handoff_status = checked.status
    record("4 · Guard 점검", "validated",
           "허용 경로와 전달 Context를 검증했습니다. 아직 책임자는 it_triage_agent입니다.", {
               "통과한 검사": ["proposed 상태", "직원 ID 일치", "현재 책임자 일치",
                           "중복 Handoff 없음", "허용 경로", "최대 인계 횟수",
                           "필수 Context 존재", "필수 값 비어 있지 않음",
                           "금지 Context Key 없음", "허용된 Context Key만 포함"],
           })
    record("5 · 점검 후 계정 지원 Agent에 전달", "validated",
           "검증된 Envelope를 계정 지원 Agent에게 전달합니다.", checked.model_dump())

    account_profile = get_agent("account_support_agent")
    account_prompt = f"""당신은 account_support_agent입니다.
검증된 Handoff: {checked.model_dump_json()}
AccountSupportResult 계약으로 다음 확인 절차를 반환하세요."""
    try:
        result, _, _ = await run_agent(
            account_profile, account_prompt, AccountSupportResult
        )
    except Exception as error:
        state.status = "failed"
        state.handoff_status = "failed"
        state.error = f"{type(error).__name__}: {error}"
        record("6 · 계정 지원 Agent 응답", "failed", state.error)
        return {**state.model_dump(), "decision": decision.model_dump(), "safe_context": safe_context}

    state.owner_agent = "account_support_agent"
    state.hop_count = checked.hop_count
    state.processed_handoff_ids.append(checked.handoff_id)
    state.handoff_status = "completed"
    state.status = "completed"
    state.result = result.model_dump()
    record("6 · 계정 지원 결과와 책임 이전", "completed",
           "계정 지원 Agent가 확인 절차를 반환한 뒤 책임을 인수했습니다.", state.result)
    return {
        **state.model_dump(),
        "decision": decision.model_dump(),
        "safe_context": safe_context,
    }
