"""수업 시작 전에 GPT, Gemini, Llama, Gemma와 Backend 상태를 확인합니다."""

import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
load_dotenv(ROOT / ".env")

from app.core.config import settings  # noqa: E402


CHECK_RESULTS: list[bool] = []


def check(label: str, success: bool, detail: str) -> None:
    CHECK_RESULTS.append(success)
    print(f"{'OK' if success else 'FAIL':<4} {label:<12} {detail}")


def main() -> int:
    CHECK_RESULTS.clear()
    check("OpenAI", bool(settings.openai_api_key), settings.openai_model)
    check("Gemini", bool(settings.gemini_api_key), settings.gemini_model)
    check("Weather", settings.weather_data_source == "live", settings.weather_data_source)
    check("Travel", settings.travel_data_source == "postgresql", settings.travel_data_source)
    try:
        import psycopg
        with psycopg.connect(settings.database_url, connect_timeout=3) as connection:
            places = connection.execute("SELECT COUNT(*) FROM mini_multi_agent_02.places WHERE source_url <> '' AND verified_at IS NOT NULL").fetchone()[0]
            budgets = connection.execute("SELECT COUNT(*) FROM mini_multi_agent_02.budget_reference WHERE source_url <> '' AND verified_at IS NOT NULL").fetchone()[0]
        check("PostgreSQL", places > 0 and budgets > 0, f"places={places}, budget_reference={budgets}")
    except Exception as error:
        check("PostgreSQL", False, f"Seed 초기화 필요: {error}")
    try:
        from redis import Redis
        with Redis.from_url(settings.redis_url, decode_responses=True) as client:
            client.ping()
        check("Redis", True, settings.redis_url)
    except Exception as error:
        check("Redis", False, str(error))
    try:
        response = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=3)
        response.raise_for_status()
        models = [item["name"] for item in response.json().get("models", [])]
        llama_ready = any(name == settings.ollama_model or name.startswith(f"{settings.ollama_model}:") for name in models)
        gemma_ready = any(name == settings.gemma_model or name.startswith(f"{settings.gemma_model}:") for name in models)
        check("Ollama", True, settings.ollama_base_url)
        check("Llama", llama_ready, settings.ollama_model)
        check("Gemma", gemma_ready, settings.gemma_model)
    except Exception as error:
        check("Ollama", False, str(error))

    try:
        response = httpx.get("http://127.0.0.1:8000/health", timeout=3)
        response.raise_for_status()
        payload = response.json()
        expected_project = "mini_multi_agent_02_role_task_contract"
        actual_project = payload.get("project")
        check(
            "Backend",
            payload.get("status") == "ok" and actual_project == expected_project,
            f"project={actual_project or 'unknown'} expected={expected_project}",
        )
    except Exception as error:
        check("Backend", False, f"Backend 실행 후 다시 확인: {error}")

    try:
        response = httpx.get("http://127.0.0.1:8000/api/mcp-status", timeout=5)
        response.raise_for_status()
        tool_count = response.json()["tool_count"]
        check("MCP", tool_count == 4, f"tools={tool_count} expected=4")
    except Exception as error:
        check("MCP", False, f"MCP와 Backend 실행 후 확인: {error}")

    print("Provider 실패는 다른 Provider나 고정 성공 결과로 대체되지 않습니다.")
    return 0 if all(CHECK_RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
