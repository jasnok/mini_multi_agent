from __future__ import annotations
import asyncio
import re
from time import perf_counter
from typing import TypeVar
import httpx
from pydantic import BaseModel
from app.core.config import settings

T = TypeVar("T", bound=BaseModel)
SUPPORTED_PROVIDERS = ("openai", "gemini", "ollama", "gemma")
PROVIDERS = SUPPORTED_PROVIDERS


class ProviderExecutionError(RuntimeError):
    def __init__(self, message: str, *, code: str, retryable: bool, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


def normalize_provider_error(provider: str, error: Exception) -> ProviderExecutionError:
    raw = str(error)
    if provider == "gemini" and ("429" in raw or "RESOURCE_EXHAUSTED" in raw):
        match = re.search(r"retry(?:Delay| in)[^0-9]*(\d+)", raw, re.IGNORECASE)
        retry_after = int(match.group(1)) if match else None
        retry_message = f" 약 {retry_after}초 후 재시도할 수 있습니다." if retry_after else " 잠시 후 다시 시도하세요."
        return ProviderExecutionError(
            "Gemini API 요청 한도를 초과했습니다." + retry_message + " 자동 Provider 대체는 수행하지 않았습니다.",
            code="quota_exhausted", retryable=True, retry_after_seconds=retry_after,
        )
    # SDK 예외의 상태 코드와 메시지만 사용합니다. 예외 전체 문자열에는 요청 정보가 섞일 수 있습니다.
    status = getattr(error, "code", None) or getattr(error, "status_code", None)
    detail = getattr(error, "message", None)
    if not isinstance(detail, str):
        detail = ""
    detail = re.sub(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,}]+", r"\1=[REDACTED]", detail)
    detail = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[REDACTED]", detail)
    detail = " ".join(detail.split())[:300]
    status_text = f" (HTTP {status})" if isinstance(status, int) else ""
    detail_text = f": {detail}" if detail else ""
    retryable = isinstance(status, int) and (status == 429 or status >= 500)
    return ProviderExecutionError(
        f"{provider} Provider 호출에 실패했습니다: {type(error).__name__}{status_text}{detail_text}",
        code="provider_error", retryable=retryable,
    )

def model_for(provider: str) -> str:
    models = {"openai": settings.openai_model, "gemini": settings.gemini_model, "ollama": settings.ollama_model, "gemma": settings.gemma_model}
    if provider not in models:
        raise ValueError(f"지원하지 않는 Provider입니다: {provider}")
    return models[provider]

def configured(provider: str) -> bool:
    if provider == "openai":
        return bool(settings.openai_api_key)
    if provider == "gemini":
        return bool(settings.gemini_api_key)
    return provider in {"ollama", "gemma"}

async def status(provider: str) -> dict[str, object]:
    result: dict[str, object] = {"configured": configured(provider), "model": model_for(provider), "reachable": None, "model_installed": None}
    if provider in {"ollama", "gemma"}:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
                response.raise_for_status()
            names = [item["name"] for item in response.json().get("models", [])]
            expected = model_for(provider)
            result.update({"reachable": True, "model_installed": any(name == expected or name.startswith(f"{expected}:") for name in names), "installed_models": names})
        except Exception as error:
            result.update({"reachable": False, "model_installed": False, "error": f"{type(error).__name__}: {error}"})
    return result

def openai_agent(prompt: str, schema: type[T]) -> T:
    from openai import OpenAI
    # 요청마다 Client를 열고 닫아 이미 종료된 HTTP Client가 재사용되지 않게 합니다.
    with OpenAI(api_key=settings.openai_api_key) as client:
        response = client.responses.parse(model=settings.openai_model, input=prompt, text_format=schema)
    if response.output_parsed is None:
        raise RuntimeError("GPT 구조화 결과가 없습니다.")
    return response.output_parsed

def gemini_agent(prompt: str, schema: type[T]) -> T:
    from google import genai
    # 요청마다 Client 생명주기를 명확히 관리하여 닫힌 Client가 재사용되지 않게 합니다.
    with genai.Client(api_key=settings.gemini_api_key) as client:
        response = client.models.generate_content(model=settings.gemini_model, contents=prompt, config={"response_mime_type": "application/json", "response_json_schema": schema.model_json_schema()})
    if not response.text:
        raise RuntimeError("Gemini 구조화 결과가 없습니다.")
    return schema.model_validate_json(response.text)

async def generate(provider: str, prompt: str, schema: type[T]) -> tuple[T, dict[str, object]]:
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"지원하지 않는 Provider입니다: {provider}")
    if provider in {"openai", "gemini"} and not configured(provider):
        raise RuntimeError(f"{provider} API Key가 없습니다.")
    started = perf_counter()
    try:
        if provider == "openai": result = await asyncio.to_thread(openai_agent, prompt, schema)
        elif provider == "gemini": result = await asyncio.to_thread(gemini_agent, prompt, schema)
        else:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(f"{settings.ollama_base_url.rstrip('/')}/api/chat", json={"model": model_for(provider), "messages": [{"role": "user", "content": prompt}], "format": schema.model_json_schema(), "stream": False})
                response.raise_for_status()
                result = schema.model_validate_json(response.json()["message"]["content"])
    except ProviderExecutionError:
        raise
    except Exception as error:
        raise normalize_provider_error(provider, error) from None
    return result, {"provider": provider, "model": model_for(provider), "latency_ms": round((perf_counter()-started)*1000, 2)}
