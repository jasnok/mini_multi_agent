import json
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.core.config import settings


@asynccontextmanager
async def tools_session():
    async with streamable_http_client(settings.mcp_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


async def list_tools() -> list[dict[str, object]]:
    async with tools_session() as session:
        tools = (await session.list_tools()).tools
        return [{"name": tool.name, "description": tool.description or ""} for tool in tools]


async def call_tool(name: str, arguments: dict[str, Any], allowed_tools: frozenset[str]) -> Any:
    if name not in allowed_tools:
        raise PermissionError(f"Agent에 허용되지 않은 MCP Tool입니다: {name}")
    async with tools_session() as session:
        server_tools = {tool.name for tool in (await session.list_tools()).tools}
        if name not in server_tools:
            raise ValueError(f"MCP Server가 제공하지 않는 Tool입니다: {name}")
        result = await session.call_tool(name, arguments=arguments)
        text = "\n".join(item.text for item in result.content if hasattr(item, "text"))
        if result.isError:
            raise RuntimeError(text or "MCP Tool 실행 실패")
        return json.loads(text) if text else None
