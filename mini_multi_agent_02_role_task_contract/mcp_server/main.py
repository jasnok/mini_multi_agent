"""mcp_server 디렉터리에서 실행: python main.py"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from mcp_server.core.config import MCP_HOST, MCP_PORT
from mcp_server.tools.travel_tools import get_budget_reference, get_lodging_reference, get_weather, search_places

mcp = FastMCP("mini-multi-agent-02-contract-tools", host=MCP_HOST, port=MCP_PORT, stateless_http=True, json_response=True)
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)

for tool in (get_weather, search_places, get_lodging_reference, get_budget_reference):
    mcp.tool(annotations=READ_ONLY)(tool)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
