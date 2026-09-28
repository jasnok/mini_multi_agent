"""Lab 09: 여행이 아닌 고객지원 업무에 같은 계약 전달 구조를 적용합니다."""

from uuid import uuid4

from app.agents.registry import get_agent
from app.agents.runtime import run_agent
from app.observability.tracker import RunTracker
from app.schemas.contracts import MultiLlmRequest, SupportCaseResult


async def run_support_flow(
    request: MultiLlmRequest,
    tracker: RunTracker | None = None,
) -> dict[str, object]:
    trace = [{"step": 1, "actor": "support_analyst_agent", "action": "started"}]
    analysis = await run_agent(
        get_agent("support_analyst_agent"), request.message, tracker=tracker
    )
    if analysis["result"] is None:
        trace.extend([
            {"step": 2, "actor": "contract_guard", "action": "analysis_rejected"},
            {"step": 3, "actor": "support_writer_agent", "action": "skipped"},
        ])
        return {
            "run_id": f"run-{uuid4().hex[:12]}", "status": "failed",
            "analysis": analysis, "response": None, "trace": trace,
        }

    verified = SupportCaseResult.model_validate(analysis["result"])
    if not verified.completed:
        trace.extend([
            {"step": 2, "actor": "contract_guard", "action": "missing_information"},
            {"step": 3, "actor": "support_writer_agent", "action": "skipped"},
        ])
        return {
            "run_id": f"run-{uuid4().hex[:12]}", "status": "needs_information",
            "analysis": analysis, "response": None,
            "missing_information": verified.missing_information, "trace": trace,
        }

    if tracker:
        tracker.advance(
            "contract_guard", "context_verified",
            "SupportCaseResult를 답변 작성 Agent에게 전달합니다.",
        )
    trace.extend([
        {"step": 2, "actor": "contract_guard", "action": "analysis_verified"},
        {"step": 3, "actor": "support_writer_agent", "action": "started"},
    ])
    response = await run_agent(
        get_agent("support_writer_agent"), request.message, verified.model_dump(), tracker
    )
    trace.append({
        "step": 4, "actor": "contract_guard",
        "action": "response_verified" if response["result"] else "response_rejected",
    })
    return {
        "run_id": f"run-{uuid4().hex[:12]}",
        "status": "completed" if response["result"] else "failed",
        "analysis": analysis, "response": response, "trace": trace,
    }


async def execute_support_tracked(
    run_id: str, request: MultiLlmRequest
) -> None:
    tracker = RunTracker(run_id, total_steps=6)
    tracker.start("고객 문의 분석을 준비하고 있습니다.")
    try:
        result = await run_support_flow(request, tracker)
        result["run_id"] = run_id
        if result["status"] in {"completed", "needs_information"}:
            tracker.finish(result)
        else:
            tracker.fail("고객지원 계약 실행이 실패했습니다.", result)
    except Exception as error:
        tracker.fail(f"{type(error).__name__}: {error}")
