import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.main import health  # noqa: E402


class ApiTests(unittest.TestCase):
    def test_health_identifies_project(self) -> None:
        self.assertEqual(health(), {"status": "ok", "project": "mini_multi_agent_04_distributed_collaboration"})


if __name__ == "__main__": unittest.main()
