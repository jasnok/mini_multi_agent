import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.runtime import _travel_arguments  # noqa: E402


class TravelArgumentTests(unittest.TestCase):
    def test_people_with_korean_subject_particle(self) -> None:
        arguments = _travel_arguments(
            "부산 3박 4일 여행을 계획해 줘. 2명이 대중교통으로 이동하고 총예산은 100만원이야."
        )

        self.assertEqual(arguments["calculate_budget"]["people"], 2)

    def test_people_without_particle(self) -> None:
        arguments = _travel_arguments(
            "부산 2박 3일 여행을 계획해 줘. 3명, 총예산은 90만원이야."
        )

        self.assertEqual(arguments["calculate_budget"]["people"], 3)

    def test_similar_unit_is_not_treated_as_people(self) -> None:
        arguments = _travel_arguments(
            "부산 1박 2일 여행에서 2인치 화면을 보고 예산은 40만원이야."
        )

        self.assertIsNone(arguments["calculate_budget"]["people"])


if __name__ == "__main__":
    unittest.main()
