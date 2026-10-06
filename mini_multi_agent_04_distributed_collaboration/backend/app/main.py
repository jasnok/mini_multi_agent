from fastapi import FastAPI
from app.routers.collaboration import router
app=FastAPI(title="Mini Multi-Agent 04 · Distributed Collaboration",version="1.0.0")
app.include_router(router)
@app.get("/health")
def health(): return {"status":"ok", "project":"mini_multi_agent_04_distributed_collaboration"}
