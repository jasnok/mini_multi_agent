import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.incident_plan import incident_plan_flow
from app.schemas.workflow import IncidentPlanRequest


REQUEST = IncidentPlanRequest(message="사내 로그인 장애 대응 계획을 작성하고 검토해 주세요.")


def supervisor(next_agent):
    return {"status": "completed", "result": {"agent_id": "incident_supervisor_agent", "next_agent": next_agent, "reason": "현재 상태"}}


def worker(agent_id, **payload):
    return {"status": "completed", "result": {"agent_id": agent_id, **payload}}


ANALYSIS = worker("incident_analyst_agent", symptoms=["로그인 실패"], impact=["일부 직원"],
                  information_to_verify=["오류 로그"], completion_criteria=["로그인 복구 확인"])
PLAN_0 = worker("incident_planner_agent", revision=0, actions=["로그 확인"], rollback_plan="설정 복원",
                verification_steps=["로그인 재시도"], addressed_feedback=[])
REVIEW_0 = worker("incident_reviewer_agent", reviewed_revision=0, approved=False,
                  feedback=["영향 범위 확인 추가"], reason="영향 범위가 빠짐")
PLAN_1 = worker("incident_planner_agent", revision=1, actions=["로그 확인", "영향 범위 확인"],
                rollback_plan="설정 복원", verification_steps=["로그인 재시도"],
                addressed_feedback=["영향 범위 확인 추가"])
REVIEW_1 = worker("incident_reviewer_agent", reviewed_revision=1, approved=True,
                  feedback=[], reason="필수 항목 확인")


class IncidentLab09Tests(unittest.IsolatedAsyncioTestCase):
    async def test_rejected_review_revises_plan_then_finishes(self):
        responses = [supervisor("incident_analyst_agent"), ANALYSIS,
                     supervisor("incident_planner_agent"), PLAN_0,
                     supervisor("incident_reviewer_agent"), REVIEW_0,
                     supervisor("incident_planner_agent"), PLAN_1,
                     supervisor("incident_reviewer_agent"), REVIEW_1,
                     supervisor("finish")]
        with patch("app.orchestration.incident_plan.run_profile", new_callable=AsyncMock, side_effect=responses) as run:
            result = await incident_plan_flow(REQUEST)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["state"]["revision_count"], 1)
        self.assertEqual(len(result["state"]["reviews"]), 2)
        self.assertNotIn("revision", run.await_args_list[3].args[2].model_fields)
        self.assertEqual(result["trace"][3]["result"]["revision"], 0)
        self.assertEqual(result["trace"][7]["result"]["revision"], 1)
        self.assertEqual(run.await_count, 11)
        self.assertIn("반드시 approved=false", run.await_args_list[5].args[1])
        self.assertNotIn("반드시 approved=false", run.await_args_list[9].args[1])
        self.assertIn("영향 범위 확인 추가", run.await_args_list[7].args[1])

    async def test_second_rejection_stops_for_human_attention(self):
        rejected_again = worker("incident_reviewer_agent", reviewed_revision=1, approved=False,
                                feedback=["추가 확인 필요"], reason="미완료")
        responses = [supervisor("incident_analyst_agent"), ANALYSIS,
                     supervisor("incident_planner_agent"), PLAN_0,
                     supervisor("incident_reviewer_agent"), REVIEW_0,
                     supervisor("incident_planner_agent"), PLAN_1,
                     supervisor("incident_reviewer_agent"), rejected_again]
        with patch("app.orchestration.incident_plan.run_profile", new_callable=AsyncMock, side_effect=responses) as run:
            result = await incident_plan_flow(REQUEST)
        self.assertEqual(result["status"], "needs_attention")
        self.assertEqual(run.await_count, 10)

    async def test_wrong_supervisor_transition_is_blocked(self):
        with patch("app.orchestration.incident_plan.run_profile", new_callable=AsyncMock,
                   return_value=supervisor("incident_reviewer_agent")) as run:
            result = await incident_plan_flow(REQUEST)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["expected_next"], "incident_analyst_agent")
        self.assertEqual(run.await_count, 1)


if __name__ == "__main__":
    unittest.main()
