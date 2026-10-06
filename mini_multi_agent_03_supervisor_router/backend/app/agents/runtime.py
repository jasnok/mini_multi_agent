"""Agent Profile과 출력 계약을 받아 실제 LLM 한 명을 실행한다."""

import json
import re
from time import perf_counter
from typing import Literal

from pydantic import create_model

from app.agents.models import AgentProfile
from app.mcp.client import call_tool
from app.providers.registry import ProviderExecutionError, generate_structured, model_for
from app.schemas.workflow import WorkerResult


def tool_arguments(tool_name: str, prompt: str) -> dict[str, object] | None:
    """사용자 요청이 포함된 Prompt에서 Tool별 필수 인자를 추출한다."""
    if tool_name == "get_order_status":
        match = re.search(r"\bORDER[-_ ]?\d+\b", prompt, re.IGNORECASE)
        return {"order_id": match.group(0).replace("_", "-").replace(" ", "-").upper()} if match else None
    if tool_name == "get_refund_policy":
        return {}
    if tool_name == "search_help_article":
        topic = next((value for value in ("로그인", "비밀번호", "앱 오류", "오류") if value in prompt), None)
        return {"topic": topic} if topic else None
    return None


async def run_profile(profile: AgentProfile, prompt: str, schema, tracker=None, *, tool_inputs=None, tool_schemas=None) -> dict[str, object]:
    started = perf_counter()
    tool_results = {}
    try:
        if tool_inputs is not None and set(tool_inputs) - profile.allowed_tools:
            raise PermissionError("Agent에 허용되지 않은 Tool 인자가 전달되었습니다.")
        for tool_name in profile.allowed_tools:
            arguments = tool_inputs.get(tool_name) if tool_inputs is not None else tool_arguments(tool_name, prompt)
            if arguments is None:
                raise ValueError(f"{tool_name} 호출에 필요한 정보가 사용자 요청에 없습니다.")
            if tracker:
                tracker.update(profile.agent_id, "tool_call", f"{tool_name} 호출 중", tool=tool_name)
            tool_results[tool_name] = await call_tool(
                tool_name, arguments, profile.allowed_tools
            )
            if tool_schemas and tool_name in tool_schemas:
                tool_results[tool_name] = tool_schemas[tool_name].model_validate(
                    tool_results[tool_name]
                ).model_dump(mode="json")
            if tracker:
                tracker.update(
                    profile.agent_id, "tool_completed", f"{tool_name} 완료",
                    done=True, tool=tool_name,
                )
        response_schema = schema
        identity_instruction = ""
        if schema is WorkerResult:
            # Worker마다 agent_id를 단일 허용값으로 제한한다. 잘못된 ID는 성공으로 고치지 않는다.
            response_schema = create_model(
                f"{profile.agent_id}_result",
                __base__=WorkerResult,
                agent_id=(Literal[profile.agent_id], ...),
            )
            identity_instruction = f"\n당신의 agent_id는 반드시 {profile.agent_id}입니다. 이전 Worker의 agent_id를 복사하지 마세요."
        grounded_prompt = (
            f"{prompt}{identity_instruction}\n"
            f"MCP Tool Result: {json.dumps(tool_results, ensure_ascii=False)}\n"
            "Tool Result에 없는 사실을 만들지 마세요."
        )
        if tracker:
            tracker.update(
                profile.agent_id, "llm_call", f"{profile.provider} 응답 대기",
                provider=profile.provider,
            )
        result, metadata = await generate_structured(profile.provider, grounded_prompt, response_schema)
        if tracker:
            tracker.update(
                profile.agent_id, "contract_verified", f"{profile.output_contract} 검증 완료",
                done=True, provider=profile.provider,
            )
        if hasattr(result, "agent_id") and result.agent_id != profile.agent_id:
            raise ValueError(f"Agent 역할 불일치: expected={profile.agent_id}, actual={result.agent_id}")
        return {
            "status": "completed", "actor": profile.agent_id, **metadata,
            "tools": sorted(profile.allowed_tools), "tool_results": tool_results,
            "result": result.model_dump(mode="json"), "error": None,
        }
    except Exception as error:
        error_code = error.code if isinstance(error, ProviderExecutionError) else "agent_error"
        retryable = error.retryable if isinstance(error, ProviderExecutionError) else False
        retry_after_seconds = error.retry_after_seconds if isinstance(error, ProviderExecutionError) else None
        return {
            "status": "failed", "actor": profile.agent_id,
            "provider_requested": profile.provider, "provider_used": None,
            "model": model_for(profile.provider),
            "latency_ms": round((perf_counter() - started) * 1000, 2),
            "fallback_used": False, "tools": sorted(profile.allowed_tools),
            "tool_results": tool_results, "result": None,
            "error": str(error), "error_code": error_code,
            "retryable": retryable, "retry_after_seconds": retry_after_seconds,
        }
