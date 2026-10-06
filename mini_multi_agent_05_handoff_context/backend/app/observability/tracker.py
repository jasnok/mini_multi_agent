from datetime import datetime, timezone
from app.schemas.contracts import HandoffState
from app.storage.redis_store import append_event, load_snapshot, save_snapshot

class HandoffTracker:
    def __init__(self, state: HandoffState):
        self.state = state
        save_snapshot(state.run_id, state.model_dump())

    def emit(self, actor: str, action: str, status: str, message: str):
        append_event(self.state.run_id, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor, "action": action, "status": status, "message": message,
            "owner_agent": self.state.owner_agent,
        })
        save_snapshot(self.state.run_id, self.state.model_dump())

    def save(self):
        save_snapshot(self.state.run_id, self.state.model_dump())

def snapshot(run_id: str):
    return load_snapshot(run_id)
