from fastapi import FastAPI
from app.routers.handoff import router

app = FastAPI(title="Mini Multi-Agent 05 · Handoff and Context", version="1.0.0")
app.include_router(router)

@app.get("/health")
def health(): return {"status": "ok", "project": "mini_multi_agent_05_handoff_context"}
