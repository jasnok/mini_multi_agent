from fastapi import APIRouter, HTTPException

from app.agents.registry import AGENTS
from app.mcp.client import list_tools
from app.providers.registry import SUPPORTED_PROVIDERS, provider_status
from app.core.config import settings
from app.schemas.runs import RunRequest, RunResult
from app.services.pattern_service import execute, find_run
from app.services.lab_catalog import LABS


router = APIRouter(prefix="/api", tags=["Orchestration Pattern Explorer"])

PATTERNS = {
    "single_agent": "하나의 Agent가 전체 요청을 처리합니다.",
    "independent": "여러 Agent를 실행하지만 전체 조정자는 없습니다.",
    "sequential": "앞 Agent 결과를 다음 Agent의 입력으로 전달합니다.",
    "parallel_join": "독립 Agent를 함께 실행하고 필수 결과를 Join합니다.",
    "router": "요청에 맞는 Worker 하나를 선택합니다.",
    "supervisor_worker": "중간 결과를 보고 다음 Worker 또는 종료를 선택합니다.",
    "handoff": "현재 책임과 최소 Context를 다음 Agent에게 넘깁니다.",
    "evaluator_reviser": "독립 평가 결과에 따라 제한된 수정을 반복합니다.",
    "orchestration_comparison": "같은 Agent를 독립 실행과 조정 실행으로 비교합니다.",
    "provider_failover": "Primary 실패 시 실제 Secondary Provider를 시도합니다.",
}

SCENARIOS = {
    "travel": "부산 2박 3일 여행을 계획해 줘. 알레르기와 대중교통, 예산 60만원을 반영해 줘.",
    "support": "ORDER-102 배송이 늦습니다. 상태와 환불 정책을 알려 주세요.",
    "content": "부산 안내문을 작성하고 출처 확인과 사용자 승인 문구를 검토해 줘.",
    "code": "사용자 입력 검증 기능을 분석하고 구현한 뒤 검토해 줘.",
}


@router.get("/patterns")
def patterns():
    return PATTERNS


@router.get("/labs")
def labs():
    return LABS


@router.get("/scenarios")
def scenarios():
    return SCENARIOS


@router.get("/agents")
def agents():
    return {
        key: {"name": value.name, "goal": value.goal, "description": value.description,
              "example_question": value.example_question, "allowed_tools": sorted(value.allowed_tools)}
        for key, value in AGENTS.items()
    }


@router.get("/providers")
async def providers():
    return {provider: await provider_status(provider) for provider in SUPPORTED_PROVIDERS}


@router.get("/mcp-status")
async def mcp_status():
    try:
        tools = await list_tools()
        return {"status": "connected", "tool_count": len(tools), "tools": tools}
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"MCP 연결 실패: {error}") from error


@router.get("/data-sources")
def data_sources():
    return {
        "weather": settings.weather_data_source,
        "travel_knowledge": "postgresql",
        "content_knowledge": "postgresql",
        "quality_requirements": "postgresql",
        "support": settings.support_data_source,
    }


@router.post("/runs", response_model=RunResult)
async def create_run(request: RunRequest) -> RunResult:
    return await execute(request)


@router.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str) -> RunResult:
    result = find_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="실행 결과를 찾을 수 없습니다.")
    return result
