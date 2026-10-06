import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.approval_flow import action_hash, decide_approval, token_hash  # noqa: E402
from app.schemas.contracts import ApprovalDecisionRequest  # noqa: E402
from app.services.demo_seed_data import hotels_for_weather  # noqa: E402


def pending_state() -> dict:
    arguments = {
        "destination": "부산",
        "days": 3,
        "preferences": ["바다"],
        "draft": {"title": "부산 여행"},
    }
    return {
        "run_id": "run-001",
        "workflow": "human_approval",
        "user_id": "user-101",
        "status": "pending_approval",
        "approval": {
            "approval_id": "approval-001",
            "action": "save_itinerary",
            "action_arguments": arguments,
            "action_hash": action_hash(arguments),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
            "status": "pending",
        },
        "draft": arguments["draft"],
        "result": None,
        "approval_token_hash": token_hash("approval-secret"),
    }


class ApprovalFlowTests(unittest.TestCase):
    def test_weather_scenarios_change_first_hotel(self) -> None:
        self.assertEqual(hotels_for_weather("rain")[0]["hotel_id"], "hotel-art")
        self.assertEqual(hotels_for_weather("clear")[0]["hotel_id"], "hotel-ocean")

    @patch("app.orchestration.approval_flow.save_demo_booking")
    @patch("app.orchestration.approval_flow.load_snapshot")
    def test_invalid_hotel_cannot_be_approved(self, load_snapshot, save_booking) -> None:
        state = pending_state()
        state["hotel_options"] = hotels_for_weather("rain")
        load_snapshot.return_value = state
        request = ApprovalDecisionRequest(
            approval_id="approval-001",
            idempotency_key="book-001",
            decision="approve",
            hotel_id="unknown-hotel",
        )
        with self.assertRaisesRegex(ValueError, "숙소를 선택"):
            decide_approval("run-001", request, "user-101", "approval-secret")
        save_booking.assert_not_called()

    @patch("app.orchestration.approval_flow.load_events", return_value=[])
    @patch("app.observability.tracker.save_snapshot")
    @patch("app.observability.tracker.append_event")
    @patch("app.orchestration.approval_flow.claim_approval_decision", return_value=True)
    @patch("app.orchestration.approval_flow.claim_idempotency", return_value="claimed")
    @patch("app.orchestration.approval_flow.save_demo_booking", return_value={"status": "demo_confirmed"})
    @patch("app.orchestration.approval_flow.load_snapshot")
    def test_selected_hotel_is_booked_after_approval(
        self, load_snapshot, save_booking, _claim_idempotency, _claim_decision,
        _append_event, _tracker_snapshot, _load_events,
    ) -> None:
        state = pending_state()
        state["hotel_options"] = hotels_for_weather("rain")
        load_snapshot.return_value = state
        request = ApprovalDecisionRequest(
            approval_id="approval-001",
            idempotency_key="book-001",
            decision="approve",
            hotel_id="hotel-art",
        )
        result = decide_approval("run-001", request, "user-101", "approval-secret")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(save_booking.call_args.args[2]["hotel"]["hotel_id"], "hotel-art")

    @patch("app.orchestration.approval_flow.save_itinerary")
    @patch("app.orchestration.approval_flow.load_snapshot", side_effect=lambda _: pending_state())
    def test_other_user_cannot_approve(self, _load_snapshot, save_itinerary) -> None:
        request = ApprovalDecisionRequest(
            approval_id="approval-001",
            idempotency_key="save-001",
            decision="approve",
        )
        with self.assertRaises(PermissionError):
            decide_approval("run-001", request, "user-999", "approval-secret")
        save_itinerary.assert_not_called()

    @patch("app.orchestration.approval_flow.save_itinerary")
    @patch("app.orchestration.approval_flow.load_snapshot", side_effect=lambda _: pending_state())
    def test_invalid_approval_token_cannot_approve(self, _load_snapshot, save_itinerary) -> None:
        request = ApprovalDecisionRequest(
            approval_id="approval-001",
            idempotency_key="save-001",
            decision="approve",
        )
        with self.assertRaisesRegex(PermissionError, "Token"):
            decide_approval("run-001", request, "user-101", "wrong-token")
        save_itinerary.assert_not_called()

    @patch("app.orchestration.approval_flow.claim_approval_decision", return_value=False)
    @patch("app.orchestration.approval_flow.load_snapshot", side_effect=lambda _: pending_state())
    def test_concurrent_approval_is_blocked(self, _load_snapshot, _claim) -> None:
        request = ApprovalDecisionRequest(
            approval_id="approval-001",
            idempotency_key="save-001",
            decision="approve",
        )
        with self.assertRaisesRegex(ValueError, "처리 중"):
            decide_approval("run-001", request, "user-101", "approval-secret")

    @patch("app.orchestration.approval_flow.load_events", return_value=[])
    @patch("app.observability.tracker.save_snapshot")
    @patch("app.observability.tracker.append_event")
    @patch("app.orchestration.approval_flow.save_snapshot")
    @patch("app.orchestration.approval_flow.claim_approval_decision", return_value=True)
    @patch("app.orchestration.approval_flow.claim_idempotency", return_value="claimed")
    @patch("app.orchestration.approval_flow.save_itinerary", return_value={"itinerary_id": "approval-001"})
    @patch("app.orchestration.approval_flow.load_snapshot", side_effect=lambda _: pending_state())
    def test_approval_executes_write_once(
        self,
        _load_snapshot,
        save_itinerary,
        _claim_idempotency,
        _claim_approval_decision,
        _save_snapshot,
        _append_event,
        _tracker_save_snapshot,
        _load_events,
    ) -> None:
        request = ApprovalDecisionRequest(
            approval_id="approval-001",
            idempotency_key="save-001",
            decision="approve",
        )
        result = decide_approval("run-001", request, "user-101", "approval-secret")
        self.assertEqual(result["status"], "completed")
        save_itinerary.assert_called_once()

    @patch("app.orchestration.approval_flow.load_events", return_value=[])
    @patch("app.observability.tracker.save_snapshot")
    @patch("app.observability.tracker.append_event")
    @patch("app.orchestration.approval_flow.claim_approval_decision", return_value=True)
    @patch("app.orchestration.approval_flow.save_itinerary")
    @patch("app.orchestration.approval_flow.load_snapshot", side_effect=lambda _: pending_state())
    def test_rejection_never_executes_write(
        self,
        _load_snapshot,
        save_itinerary,
        _claim_approval_decision,
        _append_event,
        _tracker_save_snapshot,
        _load_events,
    ) -> None:
        request = ApprovalDecisionRequest(
            approval_id="approval-001",
            idempotency_key="save-001",
            decision="reject",
            reason="일정을 수정하겠습니다.",
        )
        result = decide_approval("run-001", request, "user-101", "approval-secret")
        self.assertEqual(result["status"], "rejected")
        save_itinerary.assert_not_called()


if __name__ == "__main__":
    unittest.main()
