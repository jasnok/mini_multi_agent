"""Lab 09: 장애 분석 → 대응 계획 → 검토 → 필요 시 한 번 수정."""

import json
from uuid import uuid4

from pydantic import ValidationError

from app.agents.registry import get_agent
from app.agents.runtime import run_profile
from app.schemas.workflow import (
    IncidentAnalysisResult, IncidentPlanDraft, IncidentPlanResult, IncidentReviewDraft, IncidentReviewResult,
    IncidentPlanRequest, IncidentSupervisorDecision,
)


MAX_REVISIONS = 1
MAX_LLM_CALLS = 11
WORKER_SCHEMAS = {
    "incident_analyst_agent": IncidentAnalysisResult,
    "incident_planner_agent": IncidentPlanResult,
    "incident_reviewer_agent": IncidentReviewResult,
}


def expected_next(state: dict) -> str:
    if state["analysis"] is None:
        return "incident_analyst_agent"
    if state["plan"] is None:
        return "incident_planner_agent"
    if not state["reviews"]:
        return "incident_reviewer_agent"
    if state["reviews"][-1]["approved"]:
        return "finish"
    if state["plan"]["revision"] < state["revision_count"]:
        return "incident_planner_agent"
    if state["reviews"][-1]["reviewed_revision"] < state["plan"]["revision"]:
        return "incident_reviewer_agent"
    if state["revision_count"] >= MAX_REVISIONS:
        return "needs_attention"
    return "incident_reviewer_agent"


def worker_prompt(agent_id: str, message: str, state: dict, demonstrate_revision: bool = True) -> str:
    profile = get_agent(agent_id)
    common = f"당신은 {agent_id}입니다.\n요청: {message}\n"
    if agent_id == "incident_analyst_agent":
        return common + (
            "증상 1개, 영향 1개, 확인할 정보 1개, 완료 기준 1개를 짧게 적으세요. "
            "원인을 단정하지 마세요. IncidentAnalysisResult로 반환하세요."
        )
    if agent_id == "incident_planner_agent":
        context = {
            "analysis": state["analysis"],
            "previous_plan": state["plan"],
            "latest_feedback": state["reviews"][-1]["feedback"] if state["reviews"] else [],
        }
        return common + (
            f"필요한 정보: {json.dumps(context, ensure_ascii=False)}\n"
            "안전한 점검 단계 2개, 변경하지 않을 때의 복귀 방법, 확인 방법 1개를 짧게 적으세요. "
            "latest_feedback이 있으면 각 문구를 addressed_feedback에 그대로 넣고 계획에도 반영하세요. "
            "없으면 addressed_feedback은 빈 목록입니다. 실제 조치는 실행하지 마세요. "
            "revision은 Python이 부여합니다. IncidentPlanResult로 반환하세요."
        )
    context = {
        "completion_criteria": state["analysis"]["completion_criteria"],
        "plan": state["plan"],
        "previous_feedback": state["reviews"][-1]["feedback"] if state["reviews"] else [],
    }
    scenario_instruction = ""
    if demonstrate_revision and state["plan"]["revision"] == 0:
        scenario_instruction = (
            "이 실행은 피드백 수정 과정을 보여 주는 교육용 시나리오입니다. "
            "첫 계획에는 영향 범위를 확인하는 단계가 부족하다고 판단하고 반드시 "
            "approved=false, feedback=['영향 범위 확인 단계를 추가하세요.']로 반환하세요. "
            "이 지시는 아래의 일반 승인 기준보다 우선합니다. "
        )
    return common + (
        f"검토할 정보: {json.dumps(context, ensure_ascii=False)}\n"
        + scenario_instruction
        + "계획에 안전한 점검, 복귀 방법, 확인 방법이 있으면 approved=true, feedback=[]로 반환하세요. "
        "이전 feedback이 계획의 actions와 addressed_feedback에 반영됐다면 같은 요청을 반복하지 마세요. "
        "새로 확인된 필수 항목이 빠졌을 때만 approved=false와 수정할 항목 1개를 feedback에 적으세요. "
        "reviewed_revision은 Python이 부여합니다. IncidentReviewResult로 반환하세요."
    )


def verify_worker(agent_id: str, response: dict, state: dict):
    payload = response.get("result")
    if payload is None:
        return None, response.get("error") or "Worker 결과가 없습니다."
    try:
        verified = WORKER_SCHEMAS[agent_id].model_validate(payload)
    except ValidationError as error:
        return None, str(error)
    if agent_id == "incident_planner_agent":
        wanted = 0 if state["plan"] is None else state["revision_count"]
        if verified.revision != wanted:
            return None, f"계획 revision 불일치: expected={wanted}, actual={verified.revision}"
        if state["plan"] is not None:
            feedback = state["reviews"][-1]["feedback"]
            if not all(item in verified.addressed_feedback for item in feedback):
                return None, "수정 계획에 이전 검토 feedback 반영 내역이 없습니다."
    if agent_id == "incident_reviewer_agent" and verified.reviewed_revision != state["plan"]["revision"]:
        return None, "검토 대상 revision이 현재 계획과 다릅니다."
    return verified, None


async def incident_plan_flow(request: IncidentPlanRequest, tracker=None) -> dict[str, object]:
    state = {"analysis": None, "plan": None, "reviews": [], "revision_count": 0}
    trace = []
    while len(trace) < MAX_LLM_CALLS:
        expected = expected_next(state)
        if expected == "needs_attention":
            return {"status": "needs_attention", "reason": "review_not_approved_after_revision", "state": state, "trace": trace}
        decision_state = {
            "analysis_done": state["analysis"] is not None,
            "plan_revision": state["plan"]["revision"] if state["plan"] else None,
            "latest_review_approved": state["reviews"][-1]["approved"] if state["reviews"] else None,
            "revision_count": state["revision_count"],
        }
        supervisor_prompt = (
            "당신은 incident_supervisor_agent입니다. 다음 Agent만 고르세요.\n"
            f"진행 상태: {json.dumps(decision_state, ensure_ascii=False)}\n"
            f"현재 허용된 next_agent 값은 {expected}입니다. 정확히 이 값을 반환하세요.\n"
            "IncidentSupervisorDecision 계약으로 반환하세요."
        )
        supervisor = await run_profile(get_agent("incident_supervisor_agent"), supervisor_prompt, IncidentSupervisorDecision, tracker)
        trace.append({"step": len(trace) + 1, "actor": "incident_supervisor_agent", "action": "select", **supervisor})
        if supervisor.get("result") is None:
            return {"status": "failed", "reason": "supervisor_failed", "state": state, "trace": trace}
        selected = supervisor["result"]["next_agent"]
        if selected != expected:
            return {"status": "blocked", "reason": "invalid_transition", "expected_next": expected, "state": state, "trace": trace}
        if selected == "finish":
            return {"status": "completed", "reason": "review_approved", "state": state, "trace": trace}
        if len(trace) >= MAX_LLM_CALLS:
            break
        response_schema = (
            IncidentPlanDraft if selected == "incident_planner_agent"
            else IncidentReviewDraft if selected == "incident_reviewer_agent"
            else WORKER_SCHEMAS[selected]
        )
        worker = await run_profile(
            get_agent(selected),
            worker_prompt(selected, request.message, state, request.demonstrate_revision),
            response_schema,
            tracker,
        )
        if selected == "incident_planner_agent" and worker.get("result") is not None:
            # revision은 LLM의 추측이 아닌 검증된 실행 State에서 결정한다.
            worker["result"]["revision"] = state["revision_count"]
        if selected == "incident_reviewer_agent" and worker.get("result") is not None:
            worker["result"]["reviewed_revision"] = state["plan"]["revision"]
        verified, error = verify_worker(selected, worker, state)
        trace.append({"step": len(trace) + 1, "actor": selected, "action": "execute", "verification_error": error, **worker})
        if verified is None:
            return {"status": "failed", "reason": "worker_failed", "state": state, "trace": trace}
        if selected == "incident_analyst_agent":
            state["analysis"] = verified.model_dump()
        elif selected == "incident_planner_agent":
            state["plan"] = verified.model_dump()
        else:
            state["reviews"].append(verified.model_dump())
            if not verified.approved and state["revision_count"] < MAX_REVISIONS:
                state["revision_count"] += 1
    return {"status": "failed", "reason": "max_llm_calls", "state": state, "trace": trace}


async def execute_incident_tracked(run_id: str, request: IncidentPlanRequest) -> None:
    from app.observability.tracker import RunTracker

    tracker = RunTracker(run_id, MAX_LLM_CALLS + 1)
    tracker.update("orchestrator", "queued", "장애 대응 계획 실행이 등록되었습니다.")
    try:
        result = await incident_plan_flow(request, tracker)
        result["run_id"] = run_id
        if result["status"] == "completed":
            tracker.finish(result)
        else:
            tracker.fail(f"종료 이유: {result['reason']}", result)
    except Exception as error:
        tracker.fail(f"{type(error).__name__}: {error}")
