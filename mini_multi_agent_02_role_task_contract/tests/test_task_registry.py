import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.tasks.registry import TASKS, TASK_BY_ID  # noqa: E402


class TaskRegistryTests(unittest.TestCase):
    def test_task_definitions_are_shared_by_id(self) -> None:
        self.assertEqual(len(TASKS), 6)
        self.assertEqual(TASK_BY_ID["allocate_budget"].required_input, ["destination", "days", "people", "total_budget"])
        self.assertEqual([task.task_id for task in TASKS], ["check_weather", "find_places", "choose_lodging", "allocate_budget", "check_safety", "build_itinerary"])


if __name__ == "__main__":
    unittest.main()
