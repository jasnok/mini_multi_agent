"""mcp_server 디렉터리에서 실행: python main.py"""
import sys
from pathlib import Path

# 파일을 직접 실행해도 프로젝트 루트의 mcp_server 패키지를 찾을 수 있게 합니다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mcp_server.core.config import MCP_HOST, MCP_PORT
from mcp_server.tools.content_tools import check_required_terms, get_quality_requirements, search_facts
from mcp_server.tools.support_tools import get_order_status, get_refund_policy, search_help_article
from mcp_server.tools.travel_tools import calculate_budget, get_allergy_guidance, get_weather, search_places, search_transit


mcp = FastMCP(
    "mini-multi-agent-01-learning-tools",
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

for tool in (
    get_weather,
    search_places,
    search_transit,
    get_allergy_guidance,
    calculate_budget,
    get_order_status,
    get_refund_policy,
    search_help_article,
    search_facts,
    check_required_terms,
    get_quality_requirements,
):
    mcp.tool(annotations=READ_ONLY)(tool)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
