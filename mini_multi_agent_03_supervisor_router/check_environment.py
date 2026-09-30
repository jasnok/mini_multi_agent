"""수업 시작 전에 Provider, 공용 인프라와 API 상태를 확인합니다."""

import sys
from pathlib import Path

import httpx
import psycopg
from redis import Redis
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
    try:
        response = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=3)
        response.raise_for_status()
        models = [item["name"] for item in response.json().get("models", [])]
        check("Ollama", True, settings.ollama_base_url)
        check("Llama", any(name == settings.ollama_model or name.startswith(f"{settings.ollama_model}:") for name in models), settings.ollama_model)
        check("Gemma", any(name == settings.gemma_model or name.startswith(f"{settings.gemma_model}:") for name in models), settings.gemma_model)
    except Exception as error:
        check("Ollama", False, str(error))
    try:
        with psycopg.connect(settings.database_url, connect_timeout=3) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM mini_multi_agent_03.orders")
                order_count = cursor.fetchone()[0]
        check("PostgreSQL", True, f"orders={order_count}")
    except Exception as error:
        check("PostgreSQL", False, f"DB 초기화 확인: {error}")
    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        check("Redis", bool(redis.ping()), settings.redis_url)
        redis.close()
    except Exception as error:
        check("Redis", False, str(error))
    try:
        response = httpx.get("http://127.0.0.1:8000/health", timeout=3)
        response.raise_for_status()
        payload = response.json()
        expected_project = "mini_multi_agent_03_supervisor_router"
        actual_project = payload.get("project")
        check("Backend", payload.get("status") == "ok" and actual_project == expected_project, f"project={actual_project or 'unknown'} expected={expected_project}")
    except Exception as error:
        check("Backend", False, f"Backend 실행 후 다시 확인: {error}")
    try:
        response = httpx.get("http://127.0.0.1:8000/api/mcp-status", timeout=5)
        response.raise_for_status()
        tool_count = response.json()["tool_count"]
        check("MCP", tool_count == 3, f"tools={tool_count} expected=3")
    except Exception as error:
        check("MCP", False, f"03 Backend와 MCP 실행 후 확인: {error}")
    print("Provider 오류와 잘못된 전이는 고정된 성공 결과로 대체하지 않습니다.")
    return 0 if all(CHECK_RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
