"""
[실행 시나리오]
04의 Weather·Place·Budget·Support·Refund Agent가 사용하는 Tool을 하나의 MCP Server로
노출합니다. 날씨는 실제 Open-Meteo를 호출하고 나머지 업무 데이터는 PostgreSQL에서
조회합니다. Tool 구현은 역할별 파일에 두며 main.py는 Server 생성과 등록만 담당합니다.

mcp_server 디렉터리에서 실행합니다: python main.py
"""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mcp_server.core.config import MCP_HOST, MCP_PORT
from mcp_server.tools.support_tools import get_order_status, get_refund_policy
from mcp_server.tools.travel_tools import calculate_budget, search_places
from mcp_server.tools.weather_tools import get_weather


mcp = FastMCP("mini-multi-agent-04-tools", host=MCP_HOST, port=MCP_PORT, stateless_http=True, json_response=True)
EXTERNAL_READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
DATABASE_READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

mcp.tool(annotations=EXTERNAL_READ_ONLY)(get_weather)
mcp.tool(annotations=DATABASE_READ_ONLY)(search_places)
mcp.tool(annotations=DATABASE_READ_ONLY)(calculate_budget)
mcp.tool(annotations=DATABASE_READ_ONLY)(get_order_status)
mcp.tool(annotations=DATABASE_READ_ONLY)(get_refund_policy)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
