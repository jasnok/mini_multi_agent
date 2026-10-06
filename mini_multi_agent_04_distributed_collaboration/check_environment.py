"""Provider, Ollama, Redis, PostgreSQL, MCP, Backend 상태를 확인합니다."""
import sys
from pathlib import Path

import httpx
import psycopg
from dotenv import load_dotenv
from redis import Redis

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
load_dotenv(ROOT / ".env")

from app.core.config import settings  # noqa: E402


CHECK_RESULTS: list[bool] = []


def check(name: str, success: bool, detail: str) -> None:
    CHECK_RESULTS.append(success)
    print(f"{'OK' if success else 'FAIL':<4} {name:<16} {detail}")


def check_http(name: str, url: str) -> None:
    try:
        response = httpx.get(url, timeout=5)
        response.raise_for_status()
        check(name, True, url)
    except Exception as error:
        check(name, False, str(error))


def main() -> int:
    CHECK_RESULTS.clear()
    check("OpenAI", bool(settings.openai_api_key), settings.openai_model)
    check("Gemini", bool(settings.gemini_api_key), settings.gemini_model)
    check_http("Ollama", "http://127.0.0.1:11434/api/tags")
    try:
        response = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=5)
        response.raise_for_status()
        models = [item["name"] for item in response.json().get("models", [])]
        for label, expected in (("Llama", settings.ollama_model), ("Gemma", settings.gemma_model)):
            installed = any(name == expected or name.startswith(f"{expected}:") for name in models)
            check(label, installed, expected)
    except Exception as error:
        check("Ollama models", False, str(error))
    try:
        redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        check("Redis", bool(redis.ping()), settings.redis_url)
        redis.close()
    except Exception as error:
        check("Redis", False, str(error))

    try:
        with psycopg.connect(settings.database_url, connect_timeout=5) as database:
            place_count = database.execute(
                "SELECT COUNT(*) FROM mini_multi_agent_04.places"
            ).fetchone()[0]
        check("PostgreSQL", place_count > 0, f"장소 {place_count}건")
    except Exception as error:
        check("PostgreSQL", False, f"Schema 초기화 필요: {error}")

    try:
        response = httpx.get("http://127.0.0.1:8000/health", timeout=5)
        response.raise_for_status()
        payload = response.json()
        expected = "mini_multi_agent_04_distributed_collaboration"
        actual = payload.get("project")
        check("Backend", payload.get("status") == "ok" and actual == expected, f"project={actual or 'unknown'} expected={expected}")
    except Exception as error:
        check("Backend", False, str(error))
    try:
        response = httpx.get("http://127.0.0.1:8000/api/mcp-status", timeout=5)
        response.raise_for_status()
        payload = response.json()
        tool_count = payload.get("tool_count", len(payload.get("tools", [])))
        check("MCP via Backend", tool_count == 5, f"tools={tool_count} expected=5")
    except Exception as error:
        check("MCP via Backend", False, str(error))
    return 0 if all(CHECK_RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
