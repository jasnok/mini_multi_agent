"""Mini 06 실행 전 Redis, MCP, OpenAI Key, Gemma 설치 상태를 확인합니다."""

import asyncio
import sys
from pathlib import Path

import httpx
from redis import Redis

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings
from app.providers.registry import status


CHECK_RESULTS: list[bool] = []


def check(name: str, success: bool, detail: str) -> None:
    CHECK_RESULTS.append(success)
    print(f"{'OK' if success else 'FAIL':<4} {name:<12} {detail}")


async def main() -> int:
    CHECK_RESULTS.clear()
    for provider in ("openai", "gemma"):
        provider_status = await status(provider)
        ready = bool(provider_status["configured"])
        if provider == "gemma":
            ready = ready and bool(provider_status["reachable"]) and bool(provider_status["model_installed"])
        check(provider, ready, str(provider_status))
    try:
        with Redis.from_url(settings.redis_url, decode_responses=True) as redis:
            redis.ping()
        check("Redis", True, settings.redis_url)
    except Exception as error:
        check("Redis", False, str(error))
    try:
        response = httpx.get("http://127.0.0.1:8000/health", timeout=5); response.raise_for_status()
        payload = response.json()
        expected = "mini_multi_agent_06_security_guardrails"
        actual = payload.get("project")
        check("Backend", payload.get("status") == "ok" and actual == expected, f"project={actual or 'unknown'} expected={expected}")
    except Exception as error:
        check("Backend", False, str(error))
    try:
        response = httpx.get("http://127.0.0.1:8000/api/mcp-status", timeout=5); response.raise_for_status()
        payload = response.json()
        check("MCP", payload.get("reachable") is True and payload.get("tool_count") == 1, f"tools={payload.get('tool_count')} expected=1")
    except Exception as error:
        check("MCP", False, str(error))
    return 0 if all(CHECK_RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
