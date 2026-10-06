import json
from contextlib import asynccontextmanager

from app.core.config import settings


@asynccontextmanager
async def session():
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with streamable_http_client(settings.mcp_url) as (read, write, _):
        async with ClientSession(read, write) as client:
            await client.initialize()
            yield client


async def call(name: str, arguments: dict[str, object], allowed: set[str]):
    if name not in allowed:
        raise PermissionError(f"허용되지 않은 Tool: {name}")
    async with session() as client:
        available = {tool.name for tool in (await client.list_tools()).tools}
        if name not in available:
            raise ValueError(f"MCP Server에 없는 Tool입니다: {name}")
        result = await client.call_tool(name, arguments=arguments)
        text = "\n".join(item.text for item in result.content if hasattr(item, "text"))
        if result.isError:
            raise RuntimeError(text or "MCP Tool 실행 실패")
        return json.loads(text)


async def list_tools():
    async with session() as client:
        tools = (await client.list_tools()).tools
        return [{"name": tool.name, "description": tool.description or ""} for tool in tools]
