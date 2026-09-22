from fastapi import FastAPI

from app.routers.patterns import router


app = FastAPI(
    title="Mini Multi-Agent 01 · Orchestration Pattern Explorer",
    description="실제 GPT·Gemini·Llama·Gemma와 HTTP MCP Tool로 다양한 Orchestration Pattern을 비교합니다.",
    version="1.0.0",
)
app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Mini Multi-Agent 01 API", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
