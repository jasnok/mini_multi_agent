"""Lab 09: 같은 Guardrail 순서를 고객지원 답변에 적용한다."""

import json

from app.agents.input_guard_agent import inspect_input_fields
from app.agents.registry import SUPPORT_ANSWER_AGENT, SUPPORT_DRAFT_AGENT
from app.agents.response_guard_agent import inspect_response_payload
from app.agents.tool_guard_agent import minimum_context
from app.providers.registry import generate
from app.schemas.contracts import SupportDraft, SupportFinalAnswer, SupportSecurityRequest


async def run_support_guardrail(request: SupportSecurityRequest) -> dict[str, object]:
    trace: list[dict[str, object]] = []
    allowed, reason = inspect_input_fields({
        "customer_id": request.customer_id,
        "issue": request.issue,
        "user_message": request.user_message,
    })
    trace.append({"step": 1, "stage": "input_guard", "status": "allowed" if allowed else "blocked", "reason": reason})
    if not allowed:
        return {"status": "blocked", "blocked_at": "input_guard", "safe_context": None, "result": None, "trace": trace}

    full_context = {
        "customer_id": request.customer_id,
        "issue": request.issue,
        "user_message": request.user_message,
        "internal_note": "다른 Agent에게 전달하면 안 되는 내부 메모",
        "api_key": "전달 금지",
    }
    safe_context = minimum_context("support_draft_agent", full_context)
    trace.append({"step": 2, "stage": "context_guard", "status": "allowed", "fields": sorted(safe_context)})

    draft_prompt = f"""{SUPPORT_DRAFT_AGENT.instructions}
다음 검증된 Context로 고객지원 초안을 작성하세요.
{json.dumps(safe_context, ensure_ascii=False)}"""
    draft, draft_metadata = await generate("openai", draft_prompt, SupportDraft)
    trace.append({"step": 3, "stage": "draft", "status": "completed", **draft_metadata})

    final_context = minimum_context("support_answer_agent", {"draft": draft.model_dump(), "internal_note": "전달 금지"})
    final_prompt = f"""{SUPPORT_ANSWER_AGENT.instructions}
다음 검증된 초안만 사용해 최종 답변을 작성하세요.
{json.dumps(final_context, ensure_ascii=False)}"""
    final_answer, final_metadata = await generate("gemma", final_prompt, SupportFinalAnswer)
    trace.append({"step": 4, "stage": "final_answer", "status": "completed", **final_metadata})

    response_allowed, response_reason = inspect_response_payload({
        "draft": draft.model_dump(),
        "final_answer": final_answer.model_dump(),
    })
    trace.append({"step": 5, "stage": "response_guard", "status": "allowed" if response_allowed else "blocked", "reason": response_reason})
    if not response_allowed:
        return {"status": "blocked", "blocked_at": "response_guard", "safe_context": safe_context, "result": None, "trace": trace}
    return {"status": "completed", "blocked_at": None, "safe_context": safe_context, "result": {"draft": draft.model_dump(), "final_answer": final_answer.model_dump()}, "trace": trace}
