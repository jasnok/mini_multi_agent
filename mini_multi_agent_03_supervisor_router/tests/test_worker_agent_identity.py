import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.registry import get_agent
from app.agents.runtime import run_profile
from app.schemas.workflow import WorkerResult


class WorkerAgentIdentityTests(unittest.IsolatedAsyncioTestCase):
    async def test_reviewer_schema_requires_reviewer_identity(self):
        async def fake_generate(provider, prompt, schema):
            assert "agent_id는 반드시 reviewer_agent" in prompt
            assert schema.model_json_schema()["properties"]["agent_id"]["const"] == "reviewer_agent"
            result = schema.model_validate({"agent_id": "reviewer_agent", "summary": "검토 완료"})
            return result, {"provider_requested": provider, "provider_used": provider, "model": "test-model"}

        with patch("app.agents.runtime.generate_structured", new_callable=AsyncMock, side_effect=fake_generate):
            response = await run_profile(get_agent("reviewer_agent"), "검토해 주세요", WorkerResult)
        self.assertEqual(response["status"], "completed")
        self.assertEqual(response["result"]["agent_id"], "reviewer_agent")

    async def test_previous_worker_identity_is_rejected(self):
        async def fake_generate(provider, prompt, schema):
            with self.assertRaises(ValidationError):
                schema.model_validate({"agent_id": "analyst_agent", "summary": "검토 완료"})
            raise ValueError("role mismatch")

        with patch("app.agents.runtime.generate_structured", new_callable=AsyncMock, side_effect=fake_generate):
            response = await run_profile(get_agent("reviewer_agent"), "검토해 주세요", WorkerResult)
        self.assertEqual(response["status"], "failed")
        self.assertIsNone(response["result"])


if __name__ == "__main__":
    unittest.main()
