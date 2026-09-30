import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.runtime import tool_arguments  # noqa: E402


class ToolArgumentTests(unittest.TestCase):
    def test_order_id_is_read_from_request(self) -> None:
        self.assertEqual(tool_arguments("get_order_status", "ORDER-777 배송 상태를 알려 주세요."), {"order_id": "ORDER-777"})

    def test_order_tool_does_not_use_hidden_default(self) -> None:
        self.assertIsNone(tool_arguments("get_order_status", "배송 상태를 알려 주세요."))

    def test_help_topic_is_read_from_request(self) -> None:
        self.assertEqual(tool_arguments("search_help_article", "비밀번호 오류 해결 방법"), {"topic": "비밀번호"})

    def test_refund_policy_has_no_arguments(self) -> None:
        self.assertEqual(tool_arguments("get_refund_policy", "환불 정책"), {})


if __name__ == "__main__":
    unittest.main()
