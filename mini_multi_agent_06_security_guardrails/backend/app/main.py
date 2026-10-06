from fastapi import FastAPI

from app.routers.security import router


app = FastAPI(title="Mini Multi-Agent 06 · AI Security and Guardrails", version="1.0.0")
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "project": "mini_multi_agent_06_security_guardrails"}
