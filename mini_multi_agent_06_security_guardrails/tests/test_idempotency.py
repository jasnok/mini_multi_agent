import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.storage.redis_store import claim_idempotency  # noqa: E402


class FakeRedis:
    def __init__(self): self.values = {}
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values: return False
        self.values[key] = value; return True
    def get(self, key): return self.values.get(key)


class IdempotencyTests(unittest.TestCase):
    def test_same_request_reuses_and_changed_request_conflicts(self) -> None:
        fake = FakeRedis()
        with patch("app.storage.redis_store.client", return_value=fake):
            first = claim_idempotency("user-1", "save-1", {"destination": "부산", "days": 3})
            repeated = claim_idempotency("user-1", "save-1", {"destination": "부산", "days": 3})
            conflict = claim_idempotency("user-1", "save-1", {"destination": "제주", "days": 3})
        self.assertEqual((first, repeated, conflict), ("claimed", "reused", "conflict"))


if __name__ == "__main__": unittest.main()
