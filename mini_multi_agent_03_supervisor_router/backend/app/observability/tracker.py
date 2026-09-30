from datetime import datetime, timezone

from app.storage.redis_store import add_event, events, load_state, save_state


class RunTracker:
    """한 실행의 현재 상태는 Hash, 누적 이력은 Stream에 기록합니다."""

    def __init__(self, run_id: str, total_steps: int):
        self.run_id = run_id
        self.total_steps = total_steps
        self.completed = 0

    def update(self, actor, stage, message, done=False, status="running", **details):
        if done:
            self.completed = min(self.completed + 1, self.total_steps)
        state = {
            "run_id": self.run_id,
            "status": status,
            "current_agent": actor,
            "current_stage": stage,
            "completed_steps": self.completed,
            "total_steps": self.total_steps,
            "progress_percent": int(self.completed / self.total_steps * 100),
            "message": message,
            "result": None,
            "error": None,
        }
        save_state(self.run_id, state)
        add_event(
            self.run_id,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": actor,
                "action": stage,
                "status": "completed" if done else "started",
                "message": message,
                "details": details,
            },
        )

    def finish(self, result):
        self.completed = self.total_steps
        save_state(self.run_id, {
            "run_id": self.run_id, "status": "completed", "current_agent": None,
            "current_stage": "finished", "completed_steps": self.completed,
            "total_steps": self.total_steps, "progress_percent": 100,
            "message": "실행 완료", "result": result, "error": None,
        })

    def fail(self, error, result=None):
        save_state(self.run_id, {
            "run_id": self.run_id, "status": "failed", "current_agent": None,
            "current_stage": "failed", "completed_steps": self.completed,
            "total_steps": self.total_steps,
            "progress_percent": int(self.completed / self.total_steps * 100),
            "message": error, "result": result, "error": error,
        })


def snapshot(run_id: str):
    state = load_state(run_id)
    return {"state": state, "events": events(run_id)} if state else None
