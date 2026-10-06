from datetime import datetime, timezone
from app.storage.redis_store import append_event, load_snapshot, save_snapshot

class DistributedTracker:
    def __init__(self, run_id: str, total_steps: int = 5):
        self.run_id, self.total_steps, self.completed_steps = run_id, total_steps, 0
        self.results, self.errors = {}, {}

    def emit(self, actor: str, action: str, status: str, message: str, result=None):
        if status in {"completed", "failed", "blocked"}:
            self.completed_steps = min(self.completed_steps + 1, self.total_steps)
        if result is not None: self.results[actor] = result
        if status == "failed": self.errors[actor] = message
        append_event(self.run_id, {"timestamp": datetime.now(timezone.utc).isoformat(), "actor": actor, "action": action, "status": status, "message": message})
        save_snapshot(self.run_id, self.snapshot("running", message))

    def finish(self, result: dict):
        self.completed_steps = self.total_steps
        save_snapshot(self.run_id, self.snapshot("completed", "분산 협업 완료", result))
        self._terminal_event("workflow_completed", "completed", "분산 협업 완료")

    def fail(self, message: str, result=None):
        save_snapshot(self.run_id, self.snapshot("failed", message, result))
        self._terminal_event("workflow_failed", "failed", message)

    def _terminal_event(self, action, status, message):
        append_event(self.run_id, {"timestamp": datetime.now(timezone.utc).isoformat(), "actor": "coordinator_agent", "action": action, "status": status, "message": message})

    def snapshot(self, status="queued", message="실행 대기", result=None):
        return {"run_id": self.run_id, "status": status, "completed_steps": self.completed_steps, "total_steps": self.total_steps, "progress_percent": int(self.completed_steps / self.total_steps * 100), "message": message, "results": self.results, "errors": self.errors, "result": result}

def get_snapshot(run_id: str):
    return load_snapshot(run_id)
