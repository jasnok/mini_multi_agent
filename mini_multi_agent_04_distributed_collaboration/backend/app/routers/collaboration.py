import asyncio
import json
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.agents.registry import AGENTS, TEAMS
from app.observability.tracker import DistributedTracker, get_snapshot
from app.providers.registry import PROVIDERS, status
from app.schemas.contracts import PlanValidationRequest, RunRequest, TravelDecisionRequest, OrderRunRequest
from app.orchestration.engine import RUNS, distributed, distributed_tracked, handoff, join, parallel, partial_policy, plan, sequential, validate_plan
from app.mcp.client import list_tools
from app.storage.redis_store import read_events
from app.services.catalog import LABS
from app.orchestration.event_flow import event_collaboration
from app.orchestration.order_flow import order_collaboration
from app.orchestration.langgraph_flow import run_langgraph_travel
from app.orchestration.weather_place_budget_graph import run_weather_place_budget

router=APIRouter(prefix="/api",tags=["Distributed Collaboration"])

@router.get("/labs")
def labs(): return LABS
@router.get("/execution-plan")
def execution_plan(): return plan().model_dump()
@router.post("/plans/validate")
def plans_validate(request: PlanValidationRequest): return validate_plan(request.plan)
@router.get("/providers")
async def providers(): return {name:await status(name) for name in PROVIDERS}
@router.get("/mcp-status")
async def mcp_status():
    tools = await list_tools()
    return {"status":"connected", "tool_count":len(tools), "tools":tools}
@router.get("/registry")
def registry():
    return {
        "agents": {agent_id: {"name": profile.name, "goal": profile.goal, "provider": profile.provider, "allowed_tools": sorted(profile.allowed_tools), "defined_in": "python" if agent_id in {"coordinator_agent", "itinerary_agent"} else "yaml"} for agent_id, profile in AGENTS.items()},
        "teams": TEAMS,
    }
@router.post("/runs/sequential")
async def run_sequential(request: RunRequest): return await sequential(request.message)
@router.post("/runs/parallel")
async def run_parallel(request: RunRequest):
    state=await parallel(request.message,request.fail_agent); result=state.model_dump(); RUNS[state.run_id]=result; return result
@router.post("/runs/join")
async def run_join(request: RunRequest): return await join(request.message,request.fail_agent,request.policy)
@router.post("/runs/partial-failure")
async def run_partial(request: RunRequest): return partial_policy(await parallel(request.message,request.fail_agent),request.policy)
@router.post("/runs/handoff")
async def run_handoff(request: RunRequest, inject_secret: bool=False): return await handoff(request.message,inject_secret)
@router.post("/runs/distributed")
async def run_distributed(request: RunRequest): return await distributed(request.message)
@router.post("/runs/event-collaboration")
async def run_event_collaboration(request: RunRequest): return await event_collaboration(request.message)
@router.post("/runs/order-confirmation")
async def run_order_confirmation(request: OrderRunRequest):
    return await order_collaboration(request.message, request.fail_agent)

@router.post("/runs/langgraph")
async def run_langgraph(request: RunRequest): return await run_langgraph_travel(request.message)
@router.post("/runs/weather-place-budget")
async def run_weather_decision(request: TravelDecisionRequest):
    return await run_weather_place_budget(
        request.message, request.budget_limit, request.rain_threshold,
        request.rain_probability_override,
    )
@router.get("/runs/{run_id}")
def get_run(run_id: str):
    if run_id not in RUNS: raise HTTPException(404,"실행 결과가 없습니다.")
    return RUNS[run_id]


@router.post("/stream-runs/distributed")
async def create_stream_run(request: RunRequest, background_tasks: BackgroundTasks):
    run_id = f"run-{uuid4().hex[:12]}"
    DistributedTracker(run_id).emit(
        "coordinator_agent", "queued", "started", "분산 협업 실행 대기"
    )
    background_tasks.add_task(distributed_tracked, run_id, request.message)
    return {"run_id": run_id, "status": "queued"}


@router.get("/stream-runs/{run_id}/snapshot")
def stream_snapshot(run_id: str):
    state = get_snapshot(run_id)
    if state is None:
        raise HTTPException(404, "실행 상태가 없습니다.")
    return state


@router.get("/stream-runs/{run_id}/events")
async def stream_events(run_id: str, request: Request):
    if get_snapshot(run_id) is None:
        raise HTTPException(404, "실행 상태가 없습니다.")

    async def event_generator():
        last_id = request.headers.get("last-event-id", "0-0")
        while not await request.is_disconnected():
            events = read_events(run_id, last_id)
            for event in events:
                last_id = event["event_id"]
                yield f"id: {last_id}\nevent: trace\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            state = get_snapshot(run_id)
            if state and state["status"] in {"completed", "failed"}:
                yield f"event: finished\ndata: {json.dumps(state, ensure_ascii=False)}\n\n"
                break
            yield ": heartbeat\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
