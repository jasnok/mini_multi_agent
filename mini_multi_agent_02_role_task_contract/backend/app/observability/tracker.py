"""Orchestration 코드가 Redis 구현을 몰라도 진행 상태를 기록하게 한다."""
from datetime import datetime, timezone
from app.storage.redis_store import append_event, load_events, load_state, save_state


class RunTracker:
    def __init__(self, run_id: str, total_steps: int):
        self.run_id = run_id
        self.total_steps = total_steps
        self.completed_steps = 0

    def start(self, message: str) -> None:
        self._state("running", None, "workflow_started", message)
        self.event("orchestrator", "workflow_started", "completed", message)

    def advance(self, actor: str, stage: str, message: str, **details: object) -> None:
        self.completed_steps = min(self.completed_steps + 1, self.total_steps)
        self._state("running", actor, stage, message)
        self.event(actor, stage, "completed", message, **details)

    def waiting(self, actor: str, stage: str, message: str, **details: object) -> None:
        self._state("running", actor, stage, message)
        self.event(actor, stage, "started", message, **details)

    def finish(self, result: dict[str, object]) -> None:
        self.completed_steps = self.total_steps
        self._state("completed", None, "workflow_completed", "모든 실행이 완료되었습니다.", result=result)
        self.event("orchestrator", "workflow_completed", "completed", "모든 실행이 완료되었습니다.")

    def fail(self, message: str, result: dict[str, object] | None = None) -> None:
        self._state("failed", None, "workflow_failed", message, result=result, error=message)
        self.event("orchestrator", "workflow_failed", "failed", message)

    def event(self, actor: str, action: str, status: str, message: str, **details: object) -> None:
        append_event(self.run_id, {"timestamp": datetime.now(timezone.utc).isoformat(), "actor": actor, "action": action, "status": status, "message": message, "details": details})

    def _state(self, status: str, current_agent: str | None, current_stage: str, message: str, **extra: object) -> None:
        state = {"run_id": self.run_id, "status": status, "current_agent": current_agent, "current_stage": current_stage, "completed_steps": self.completed_steps, "total_steps": self.total_steps, "progress_percent": int(self.completed_steps / self.total_steps * 100), "message": message, "result": None, "error": None, **extra}
        save_state(self.run_id, state)


def snapshot(run_id: str) -> dict[str, object] | None:
    state = load_state(run_id)
    return {"state": state, "events": load_events(run_id)} if state else None
