"""05 실행 전에 Provider, Redis, MCP와 Backend를 확인합니다."""

import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv
from redis import Redis

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
load_dotenv(ROOT / ".env")

from app.core.config import settings  # noqa: E402


CHECK_RESULTS: list[bool] = []


def check(name: str, success: bool, detail: str):
    CHECK_RESULTS.append(success)
    print(f"{'OK' if success else 'FAIL':<4} {name:<10} {detail}")


def main() -> int:
    CHECK_RESULTS.clear()
    check("OpenAI", bool(settings.openai_api_key), settings.openai_model)
    try:
        response = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=3)
        response.raise_for_status()
        models = [item["name"] for item in response.json().get("models", [])]
        check("Ollama", True, settings.ollama_base_url)
        expected = settings.gemma_model
        installed = any(name == expected or name.startswith(f"{expected}:") for name in models)
        check("Gemma", installed, expected)
    except Exception as error:
        check("Ollama", False, str(error))
    try:
        redis = Redis.from_url(settings.redis_url)
        check("Redis", bool(redis.ping()), settings.redis_url)
        redis.close()
    except Exception as error:
        check("Redis", False, str(error))
    try:
        response = httpx.get("http://127.0.0.1:8000/health", timeout=5); response.raise_for_status()
        payload = response.json()
        expected = "mini_multi_agent_05_handoff_context"
        actual = payload.get("project")
        check("Backend", payload.get("status") == "ok" and actual == expected, f"project={actual or 'unknown'} expected={expected}")
    except Exception as error:
        check("Backend", False, str(error))
    try:
        response = httpx.get("http://127.0.0.1:8000/api/mcp-status", timeout=5); response.raise_for_status()
        payload = response.json()
        tool_count = payload.get("tool_count", len(payload.get("tools", [])))
        check("MCP", tool_count == 1, f"tools={tool_count} expected=1")
    except Exception as error:
        check("MCP", False, str(error))
    return 0 if all(CHECK_RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
