import json

from app.agents.registry import RESPONSE_GUARD_AGENT, TRAVEL_AGENT
from app.providers.registry import generate
from app.schemas.contracts import FinalAnswer, TravelDraft


async def create_travel_draft(context: dict[str, object]) -> tuple[TravelDraft, dict[str, object]]:
    prompt = f"""{TRAVEL_AGENT.instructions}

다음 검증된 Context로 여행 초안을 작성하세요.
{json.dumps(context, ensure_ascii=False)}
"""
    return await generate("openai", prompt, TravelDraft)


async def revise_final_answer(draft: TravelDraft) -> tuple[FinalAnswer, dict[str, object]]:
    prompt = f"""{RESPONSE_GUARD_AGENT.instructions}

다음 초안을 초보 사용자가 읽기 쉬운 최종 답변으로 정리하세요.
예약·결제가 완료되었다고 주장하지 마세요.
{draft.model_dump_json()}
"""
    return await generate("gemma", prompt, FinalAnswer)
