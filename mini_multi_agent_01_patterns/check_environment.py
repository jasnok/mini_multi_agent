"""수업 시작 전에 Provider, Ollama, MCP, Backend 상태를 확인합니다."""

import os
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
    check("Support", settings.support_data_source == "postgresql", settings.support_data_source)

    try:
        import psycopg
        tables = ("orders", "refund_policies", "help_articles", "travel_places",
                  "transit_guides", "allergy_guidance", "content_facts", "quality_requirements")
        counts = {}
        with psycopg.connect(settings.database_url, connect_timeout=3) as connection:
            for table in tables:
                counts[table] = connection.execute(
                    f"SELECT COUNT(*) FROM mini_multi_agent_01.{table}"
                ).fetchone()[0]
        check("PostgreSQL", all(counts.values()), str(counts))
    except Exception as error:
        check("PostgreSQL", False, f"Seed 초기화 필요: {error}")

    try:
        response = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=3)
        response.raise_for_status()
        models = [item["name"] for item in response.json().get("models", [])]
        check("Ollama", True, f"models={models}")
        llama_ready = any(name == settings.ollama_model or name.startswith(f"{settings.ollama_model}:") for name in models)
        gemma_ready = any(name == settings.gemma_model or name.startswith(f"{settings.gemma_model}:") for name in models)
        check("Llama", llama_ready, settings.ollama_model)
        check("Gemma", gemma_ready, settings.gemma_model)
    except Exception as error:
        check("Ollama", False, str(error))

    try:
        response = httpx.get("http://127.0.0.1:8000/api/mcp-status", timeout=5)
        response.raise_for_status()
        payload = response.json()
        check("MCP", payload["tool_count"] == 11, f"tools={payload['tool_count']} expected=11")
    except Exception as error:
        check("MCP", False, f"MCP와 Backend 실행 후 다시 확인: {error}")

    configured_count = sum([bool(settings.openai_api_key), bool(settings.gemini_api_key)])
    if configured_count == 0:
        print("\nOpenAI/Gemini Key가 없습니다. Ollama를 사용하거나 .env를 설정하세요.")
    print("Provider 실패는 다른 Provider의 성공으로 자동 대체되지 않습니다.")
    return 0 if all(CHECK_RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
