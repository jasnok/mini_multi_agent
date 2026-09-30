from fastapi import FastAPI

from app.routers.workflow import router


app = FastAPI(title="Mini Multi-Agent 03 · Supervisor and Router", description="Rule Router, LLM Router, Supervisor State와 세 Worker의 협업을 학습합니다.", version="1.0.0")
app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Mini Multi-Agent 03 API", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "project": "mini_multi_agent_03_supervisor_router"}
