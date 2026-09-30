from fastapi import APIRouter, BackgroundTasks, HTTPException
from uuid import uuid4

from app.providers.registry import SUPPORTED_PROVIDERS, provider_status
from app.schemas.workflow import IncidentPlanRequest, MessageRequest, RouterValidationRequest, SupervisorRequest
from app.services.catalog import ARCHITECTURE_CASES, LABS, ROUTER_CASES, ROUTING_VALIDATION_CASES
from app.services.workflow_service import execute_tracked, full_supervisor_team, llm_router_flow, rule_router_agent, small_supervisor_loop, supervisor_decision, validate_route
from app.agents.registry import AGENTS
from app.mcp.client import list_tools
from app.observability.tracker import RunTracker, snapshot
from app.orchestration.internal_flow import execute_internal_tracked, run_internal_router_flow
from app.orchestration.incident_plan import execute_incident_tracked, incident_plan_flow


router = APIRouter(prefix="/api", tags=["Supervisor and Router"])


@router.get("/labs")
def labs():
    return LABS


@router.get("/rule-router")
def rule_router():
    return [{**case, "decision": rule_router_agent(case["message"]).model_dump()} for case in ROUTER_CASES]


@router.get("/routing-validation-cases")
def routing_validation_cases():
    return ROUTING_VALIDATION_CASES


@router.post("/routing/validate")
def routing_validate(request: RouterValidationRequest):
    return validate_route(request.payload)


@router.get("/architecture-cases")
def architecture_cases():
    return ARCHITECTURE_CASES


@router.get("/providers")
async def providers():
    return {provider: await provider_status(provider) for provider in SUPPORTED_PROVIDERS}


@router.get("/agents")
def agents():
    return {key: {"name": value.name, "goal": value.goal, "description": value.description, "provider": value.provider, "output_contract": value.output_contract, "allowed_tools": sorted(value.allowed_tools), "defined_in": "python" if key in {"router_agent", "internal_router_agent", "supervisor_agent"} else "yaml"} for key, value in AGENTS.items()}


@router.get("/mcp-status")
async def mcp_status():
    try:
        tools = await list_tools()
        return {"status": "connected", "tool_count": len(tools), "tools": tools}
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"MCP 연결 실패: {error}") from error


@router.post("/runs/router")
async def run_router(request: MessageRequest):
    return await llm_router_flow(request)


@router.post("/runs/supervisor-decision")
async def run_supervisor_decision(request: SupervisorRequest):
    return await supervisor_decision(request)


@router.post("/runs/supervisor-loop")
async def run_supervisor_loop(request: MessageRequest):
    return await small_supervisor_loop(request)


@router.post("/runs/multi-llm-team")
async def run_multi_llm_team(request: MessageRequest):
    return await full_supervisor_team(request)


@router.post("/runs/internal-router")
async def run_internal_router(request: MessageRequest):
    return await run_internal_router_flow(request)


@router.post("/runs/incident-plan")
async def run_incident_plan(request: IncidentPlanRequest):
    return await incident_plan_flow(request)


@router.post("/async-runs/{flow_name}")
async def create_async_run(flow_name: str, request: IncidentPlanRequest, background_tasks: BackgroundTasks):
    if flow_name not in {"router", "supervisor-loop", "supervisor-team", "internal-router", "incident-plan"}:
        raise HTTPException(status_code=400, detail="지원하지 않는 실행 흐름입니다.")
    total_steps = {"router": 4, "supervisor-loop": 5, "supervisor-team": 8, "internal-router": 4, "incident-plan": 12}[flow_name]
    run_id = f"run-{uuid4().hex[:12]}"
    RunTracker(run_id, total_steps).update(
        "orchestrator", "queued", "실행 요청이 Queue에 등록되었습니다."
    )
    if flow_name == "internal-router":
        background_tasks.add_task(execute_internal_tracked, run_id, request)
    elif flow_name == "incident-plan":
        background_tasks.add_task(execute_incident_tracked, run_id, request)
    else:
        background_tasks.add_task(execute_tracked, run_id, flow_name, request)
    return {"run_id": run_id, "status": "queued"}


@router.get("/async-runs/{run_id}/snapshot")
def get_snapshot(run_id: str):
    value = snapshot(run_id)
    if value is None:
        raise HTTPException(status_code=404, detail="실행 상태를 찾을 수 없습니다.")
    return value
