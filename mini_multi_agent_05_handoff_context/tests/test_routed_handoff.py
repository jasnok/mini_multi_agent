import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.routed_handoff import route_blueprints, run_routed_handoff  # noqa: E402
from app.schemas.contracts import (  # noqa: E402
    AccessSupportResult, AccountSupportResult, DeviceSupportResult,
    RoutedSupportDecision, RoutedSupportRequest,
)


class RoutedHandoffTests(unittest.IsolatedAsyncioTestCase):
    async def test_each_route_sends_only_its_allowed_context(self):
        cases = [
            ("account_support_agent", AccountSupportResult(summary="계정 확인", next_steps=["잠금 상태 확인"]),
             {"employee_id", "system_name", "issue"}),
            ("device_support_agent", DeviceSupportResult(summary="기기 확인", next_steps=["전원 확인"]),
             {"employee_id", "issue"}),
            ("access_support_agent", AccessSupportResult(summary="승인 확인", next_steps=["승인자 확인"]),
             {"employee_id", "system_name", "issue"}),
        ]
        request = RoutedSupportRequest(issue="업무용 노트북이 켜지지 않고 프로젝트 자료에 접근할 수 없습니다.")
        self.assertEqual(len(route_blueprints()), 3)
        for target, answer, expected_keys in cases:
            with self.subTest(target=target):
                decision = RoutedSupportDecision(target_agent=target, reason="분류 결과",
                                                 responsibility="담당 분야의 확인 절차 안내")
                with patch("app.orchestration.routed_handoff.run_agent", new_callable=AsyncMock) as agent:
                    agent.side_effect = [(decision, {}, {}), (answer, {}, {})]
                    result = await run_routed_handoff(request)
                self.assertEqual(result["status"], "completed")
                self.assertEqual(result["owner_agent"], target)
                self.assertEqual(set(result["safe_context"]), expected_keys)
                self.assertEqual(result["trace"][2]["data"]["status"], "proposed")
                self.assertEqual(result["trace"][4]["data"]["status"], "validated")
                self.assertEqual(result["trace"][4]["owner_agent"], "support_router")
                self.assertEqual(result["trace"][5]["owner_agent"], target)
                self.assertIn(result["trace"][4]["data"]["handoff_id"], agent.call_args_list[1].args[1])
                self.assertEqual(agent.call_args_list[1].args[2], type(answer))

    async def test_guard_rejection_does_not_call_target(self):
        decision = RoutedSupportDecision(target_agent="device_support_agent", reason="기기 고장",
                                         responsibility="기기 확인 절차 안내")
        with patch("app.orchestration.routed_handoff.run_agent", new_callable=AsyncMock) as agent, \
             patch("app.orchestration.routed_handoff.validate_handoff", side_effect=ValueError("Guard 차단")):
            agent.return_value = (decision, {}, {})
            result = await run_routed_handoff(RoutedSupportRequest(issue="노트북 고장"))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["owner_agent"], "support_router")
        self.assertEqual(agent.await_count, 1)
        self.assertEqual(result["trace"][3]["status"], "failed")

    async def test_target_failure_keeps_router_as_owner(self):
        decision = RoutedSupportDecision(target_agent="account_support_agent", reason="로그인 문제",
                                         responsibility="계정 확인 절차 안내")
        with patch("app.orchestration.routed_handoff.run_agent", new_callable=AsyncMock) as agent:
            agent.side_effect = [(decision, {}, {}), RuntimeError("target failed")]
            result = await run_routed_handoff(RoutedSupportRequest(issue="로그인 오류"))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["owner_agent"], "support_router")
        self.assertEqual(agent.await_count, 2)
        self.assertIsNone(result["result"])


if __name__ == "__main__":
    unittest.main()
