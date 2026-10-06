"""mcp_server 디렉터리에서 실행합니다: python main.py"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from mcp_server.core.config import MCP_HOST, MCP_PORT
from mcp_server.tools.weather_tools import get_weather

mcp = FastMCP("mini-multi-agent-05-weather", host=MCP_HOST, port=MCP_PORT, stateless_http=True, json_response=True)
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
mcp.tool(annotations=READ_ONLY)(get_weather)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
