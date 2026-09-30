"""mcp_server 디렉터리에서 실행: python main.py"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from mcp_server.core.config import MCP_HOST, MCP_PORT
from mcp_server.tools.support_tools import (
    get_order_status,
    get_refund_policy,
    search_help_article,
)

mcp = FastMCP(
    "mini-multi-agent-03-support-tools",
    host=MCP_HOST,
    port=MCP_PORT,
    stateless_http=True,
    json_response=True,
)
READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

for tool in (get_order_status, get_refund_policy, search_help_article):
    mcp.tool(annotations=READ_ONLY)(tool)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
