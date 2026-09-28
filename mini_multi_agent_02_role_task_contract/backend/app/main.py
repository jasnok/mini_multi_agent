from fastapi import FastAPI

from app.routers.contracts import router


app = FastAPI(
    title="Mini Multi-Agent 02 · Role, Task and Contract Lab",
    description="Agent 역할, Task, Pydantic 계약과 실제 MCP·Multi-LLM 결과 검증을 학습합니다.",
    version="1.0.0",
)
app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Mini Multi-Agent 02 API", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "project": "mini_multi_agent_02_role_task_contract"}
