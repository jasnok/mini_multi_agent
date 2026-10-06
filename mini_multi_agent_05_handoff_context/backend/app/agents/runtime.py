import json

from app.agents.models import AgentProfile
from app.mcp.client import call
from app.providers.registry import generate


async def run_agent(
    profile: AgentProfile,
    prompt: str,
    schema,
    tool_arguments: dict[str, dict] | None = None,
):
    """Agent Profile의 허용 Tool을 실행하고 실제 LLM 결과를 계약으로 검증합니다."""
    tool_arguments = tool_arguments or {}
    tool_results = {}
    for tool_name in profile.allowed_tools:
        tool_results[tool_name] = await call(
            tool_name,
            tool_arguments.get(tool_name, {}),
            set(profile.allowed_tools),
        )
        if tool_results[tool_name].get("success") is False:
            raise RuntimeError(
                f"{tool_name} 조회 실패: {tool_results[tool_name].get('error', '원인 미상')}"
            )
    grounded_prompt = f"""{prompt}
MCP Tool Result: {json.dumps(tool_results, ensure_ascii=False)}
Tool Result에 없는 사실을 만들지 마세요."""
    result, metadata = await generate(profile.provider, grounded_prompt, schema)
    if hasattr(result, "agent_id") and result.agent_id != profile.agent_id:
        raise ValueError(
            f"Agent 역할 불일치: expected={profile.agent_id}, actual={result.agent_id}"
        )
    return result, metadata, tool_results
