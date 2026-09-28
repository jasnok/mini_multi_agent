from fastapi import APIRouter, BackgroundTasks, HTTPException
from uuid import uuid4

from app.providers.registry import SUPPORTED_PROVIDERS, provider_status
from app.schemas.contracts import MultiLlmRequest, MultiTaskMessageRequest, TaskExecutionRequest, TaskMessageRequest, ValidationRequest
from app.services.catalog import INCOMPLETE_STATES, LABS, ROLE_CARDS
from app.tasks.registry import TASKS
from app.services.contract_service import VALIDATION_CASES, contract_schemas, validate_contract
from app.services.llm_service import run_multi_llm, run_verified_flow
from app.agents.registry import AGENTS
from app.core.config import settings
from app.mcp.client import list_tools
from app.observability.tracker import RunTracker, snapshot
from app.orchestration.verified_flow import execute_tracked
from app.orchestration.support_flow import execute_support_tracked, run_support_flow
from app.orchestration.task_execution import execute_task, execute_task_from_message
from app.orchestration.multi_task_message import execute_multi_task_from_message
from app.orchestration.weather_place_lodging_budget import execute_weather_place_lodging_budget


router = APIRouter(prefix="/api", tags=["Role, Task and Contract"])


@router.get("/labs")
def labs():
    return LABS


@router.get("/role-cards")
def role_cards():
    return [card.model_dump() for card in ROLE_CARDS]


@router.get("/tasks")
def tasks():
    return [task.model_dump() for task in TASKS]


@router.post("/tasks/execute")
async def run_task(request: TaskExecutionRequest):
    return await execute_task(request)


@router.post("/tasks/execute-from-message")
async def run_task_from_message(request: TaskMessageRequest):
    return await execute_task_from_message(request)


@router.post("/tasks/execute-multi-from-message")
async def run_multi_task_from_message(request: MultiTaskMessageRequest):
    return await execute_weather_place_lodging_budget(request)


@router.get("/contracts")
def contracts():
    return contract_schemas()


@router.get("/validation-cases")
def validation_cases():
    return VALIDATION_CASES


@router.post("/contracts/validate")
def validate(request: ValidationRequest):
    return validate_contract(request)


@router.get("/incomplete-states")
def incomplete_states():
    return {name: value.model_dump() if hasattr(value, "model_dump") else value for name, value in INCOMPLETE_STATES.items()}


@router.get("/providers")
async def providers():
    return {provider: await provider_status(provider) for provider in SUPPORTED_PROVIDERS}


@router.get("/agents")
def agents():
    return {key: {"name": value.name, "goal": value.goal, "description": value.description, "example_question": value.example_question, "provider": value.provider, "output_contract": value.output_contract, "allowed_tools": sorted(value.allowed_tools)} for key, value in AGENTS.items()}


@router.get("/data-sources")
def data_sources():
    return {"weather": settings.weather_data_source, "travel": settings.travel_data_source}


@router.get("/mcp-status")
async def mcp_status():
    try:
        tools = await list_tools()
        return {"status": "connected", "tool_count": len(tools), "tools": tools}
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"MCP 연결 실패: {error}") from error


@router.post("/runs/multi-llm")
async def multi_llm(request: MultiLlmRequest):
    return await run_multi_llm(request)


@router.post("/runs/verified-flow")
async def verified_flow(request: MultiLlmRequest):
    return await run_verified_flow(request)


@router.post("/runs/support-flow")
async def support_flow(request: MultiLlmRequest):
    return await run_support_flow(request)


@router.post("/async-runs/{flow_name}")
async def create_async_run(flow_name: str, request: MultiLlmRequest, background_tasks: BackgroundTasks):
    if flow_name not in {"multi-llm", "verified-flow", "support-flow"}:
        raise HTTPException(status_code=400, detail="지원하지 않는 실행 흐름입니다.")
    run_id = f"run-{uuid4().hex[:12]}"
    total_steps = 11 if flow_name == "multi-llm" else 6
    RunTracker(run_id, total_steps).start("실행 요청이 Queue에 등록되었습니다.")
    if flow_name == "support-flow":
        background_tasks.add_task(execute_support_tracked, run_id, request)
    else:
        background_tasks.add_task(execute_tracked, run_id, flow_name, request)
    return {"run_id": run_id, "status": "queued"}


@router.get("/async-runs/{run_id}/snapshot")
def get_run_snapshot(run_id: str):
    value = snapshot(run_id)
    if value is None:
        raise HTTPException(status_code=404, detail="실행 상태를 찾을 수 없습니다.")
    return value
