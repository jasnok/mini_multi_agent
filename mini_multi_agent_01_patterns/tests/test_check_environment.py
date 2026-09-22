import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import check_environment  # noqa: E402


class CheckEnvironmentTests(unittest.TestCase):
    def test_check_records_failure(self) -> None:
        check_environment.CHECK_RESULTS.clear()

        with patch("builtins.print"):
            check_environment.check("sample", False, "unavailable")

        self.assertEqual(check_environment.CHECK_RESULTS, [False])

    def test_check_records_success(self) -> None:
        check_environment.CHECK_RESULTS.clear()

        with patch("builtins.print"):
            check_environment.check("sample", True, "ready")

        self.assertEqual(check_environment.CHECK_RESULTS, [True])


if __name__ == "__main__":
    unittest.main()
