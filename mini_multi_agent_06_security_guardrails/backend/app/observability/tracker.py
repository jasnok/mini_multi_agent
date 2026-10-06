from app.schemas.contracts import AuditEvent
from app.storage.redis_store import append_event, save_snapshot


class GuardrailTracker:
    def __init__(self, run_id: str, state: dict[str, object]):
        self.run_id = run_id
        self.state = state
        self.sequence = 0
        save_snapshot(run_id, state)

    def record(self, stage: str, agent_id: str, status: str, message: str, details: dict[str, object] | None = None) -> None:
        self.sequence += 1
        event = AuditEvent(
            sequence=self.sequence,
            stage=stage,
            agent_id=agent_id,
            status=status,
            message=message,
            details=details or {},
        ).model_dump()
        append_event(self.run_id, event)
        self.state.update({"current_stage": stage, "current_status": status, "message": message, "progress": min(self.sequence * 14, 95)})
        save_snapshot(self.run_id, self.state)

    def finish(self, status: str, result: dict[str, object] | None = None) -> None:
        self.state.update({"status": status, "current_status": status, "progress": 100, "result": result})
        save_snapshot(self.run_id, self.state)
