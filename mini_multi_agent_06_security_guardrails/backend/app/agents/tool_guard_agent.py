from app.agents.registry import load_policies


def authorize_tool(agent_id: str, tool_name: str, approved: bool = False) -> None:
    policies = load_policies()
    allowed_tools = policies["tools"].get(agent_id, [])
    if tool_name not in allowed_tools:
        raise PermissionError(f"{agent_id}에게 {tool_name} Tool 권한이 없습니다.")
    if tool_name in policies["write_tools"] and not approved:
        raise PermissionError(f"{tool_name}은 사용자 승인 후 실행할 수 있습니다.")


def minimum_context(agent_id: str, full_context: dict[str, object]) -> dict[str, object]:
    allowed_fields = load_policies()["context_access"].get(agent_id, [])
    return {field: full_context[field] for field in allowed_fields if field in full_context}
