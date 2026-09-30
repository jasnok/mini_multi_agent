import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import check_environment  # noqa: E402


class CheckEnvironmentTests(unittest.TestCase):
    def setUp(self) -> None:
        check_environment.CHECK_RESULTS.clear()

    def test_check_records_result(self) -> None:
        with patch("builtins.print"):
            check_environment.check("success", True, "ready")
            check_environment.check("failure", False, "unavailable")
        self.assertEqual(check_environment.CHECK_RESULTS, [True, False])


if __name__ == "__main__":
    unittest.main()
