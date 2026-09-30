import json
from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from app.core.config import settings

@asynccontextmanager
async def session():
    async with streamable_http_client(settings.mcp_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as client:
            await client.initialize()
            yield client

async def call_tool(name: str, arguments: dict, allowed_tools: frozenset[str]):
    if name not in allowed_tools:
        raise PermissionError(f"Agent에 허용되지 않은 Tool입니다: {name}")
    async with session() as client:
        if name not in {tool.name for tool in (await client.list_tools()).tools}:
            raise ValueError(f"MCP Server에 없는 Tool입니다: {name}")
        result = await client.call_tool(name, arguments=arguments)
        text = "\n".join(item.text for item in result.content if hasattr(item, "text"))
        if result.isError:
            raise RuntimeError(text or "MCP Tool 실행 실패")
        return json.loads(text) if text else None

async def list_tools():
    async with session() as client:
        return [{"name": tool.name, "description": tool.description or ""} for tool in (await client.list_tools()).tools]
