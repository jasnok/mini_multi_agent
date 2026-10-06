import asyncio
import json
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.agents.registry import AGENTS, HANDOFF_ROUTES
from app.observability.tracker import HandoffTracker, snapshot
from app.orchestration.engine import execute_handoff, guard_cases_demo, minimum_context_demo
from app.providers.registry import PROVIDERS, status
from app.schemas.contracts import HandoffRunRequest, HandoffState
from app.mcp.client import list_tools
from app.storage.redis_store import read_events
from app.services.catalog import LABS
from app.orchestration.internal_flow import run_internal_handoff
from app.orchestration.routed_handoff import route_blueprints, run_routed_handoff
from app.orchestration.refund_handoff import run_refund_handoff
from app.schemas.contracts import InternalHandoffRequest, RoutedSupportRequest, RefundHandoffRequest

router = APIRouter(prefix="/api", tags=["Handoff and Context"])
@router.get("/labs")
def labs(): return LABS

@router.get("/minimum-context")
def minimum_context(): return minimum_context_demo()

@router.get("/guard-cases")
def guard_cases(): return guard_cases_demo()

@router.get("/registry")
def registry():
    return {
        "agents": {key: {"name": value.name, "goal": value.goal, "provider": value.provider, "allowed_tools": sorted(value.allowed_tools), "defined_in": "python"} for key, value in AGENTS.items()},
        "handoff_routes": HANDOFF_ROUTES,
    }

@router.get("/providers")
async def providers(): return {name: await status(name) for name in PROVIDERS}

@router.get("/mcp-status")
async def mcp_status():
    tools = await list_tools()
    return {"status": "connected", "tool_count": len(tools), "tools": tools}

@router.post("/runs/handoff")
async def create_run(request: HandoffRunRequest, background_tasks: BackgroundTasks):
    run_id = f"run-{uuid4().hex[:12]}"
    HandoffTracker(HandoffState(run_id=run_id))
    background_tasks.add_task(execute_handoff, run_id, request)
    return {"run_id": run_id, "status": "queued"}

@router.post("/runs/internal-handoff")
async def internal_handoff(request: InternalHandoffRequest):
    return await run_internal_handoff(request)

@router.get("/routed-handoff/routes")
def routed_handoff_routes():
    return route_blueprints()

@router.post("/runs/routed-handoff")
async def routed_handoff(request: RoutedSupportRequest):
    return await run_routed_handoff(request)

@router.post("/runs/refund-handoff")
async def refund_handoff(request: RefundHandoffRequest):
    return await run_refund_handoff(request)

@router.get("/runs/{run_id}/snapshot")
def run_snapshot(run_id: str):
    state = snapshot(run_id)
    if state is None: raise HTTPException(404, "실행 상태가 없습니다.")
    return state

@router.get("/runs/{run_id}/events")
async def run_events(run_id: str, request: Request):
    if snapshot(run_id) is None:
        raise HTTPException(404, "실행 상태가 없습니다.")
    async def generator():
        last_id = request.headers.get("last-event-id", "0-0")
        while not await request.is_disconnected():
            for event in read_events(run_id, last_id):
                last_id = event["event_id"]
                yield f"id: {last_id}\nevent: handoff\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            state = snapshot(run_id)
            if state and state["status"] in {"completed", "failed", "rejected"}:
                yield f"event: finished\ndata: {json.dumps(state, ensure_ascii=False)}\n\n"
                break
            yield ": heartbeat\n\n"
            await asyncio.sleep(0.5)
    return StreamingResponse(generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
