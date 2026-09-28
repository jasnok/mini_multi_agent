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


class ProviderExecutionError(RuntimeError):
    """Provider 원문 대신 UI와 Trace에 노출할 안전한 실패 정보."""

    def __init__(self, message: str, *, code: str, retryable: bool, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


def normalize_provider_error(provider: str, error: Exception) -> ProviderExecutionError:
    raw = str(error)
    if provider == "gemini" and ("429" in raw or "RESOURCE_EXHAUSTED" in raw):
        retry_match = re.search(r"retry(?:Delay| in)[^0-9]*(\d+)", raw, re.IGNORECASE)
        retry_after = int(retry_match.group(1)) if retry_match else None
        suffix = f" 약 {retry_after}초 후 재시도할 수 있습니다." if retry_after else " 잠시 후 다시 시도하세요."
        return ProviderExecutionError(
            "Gemini API 요청 한도를 초과했습니다." + suffix + " 자동 Provider 대체는 수행하지 않았습니다.",
            code="quota_exhausted",
            retryable=True,
            retry_after_seconds=retry_after,
        )
    return ProviderExecutionError(
        f"{provider} Provider 호출에 실패했습니다: {type(error).__name__}",
        code="provider_error",
        retryable=False,
    )


def model_for(provider: str) -> str:
    models = {
        "openai": settings.openai_model,
        "gemini": settings.gemini_model,
        "ollama": settings.ollama_model,
        "gemma": settings.gemma_model,
    }
    if provider not in models:
        raise ValueError(f"지원하지 않는 Provider입니다: {provider}")
    return models[provider]


def configured(provider: str) -> bool:
    if provider == "openai":
        return bool(settings.openai_api_key)
    if provider == "gemini":
        return bool(settings.gemini_api_key)
    return provider in {"ollama", "gemma"}


async def provider_status(provider: str) -> dict[str, object]:
    status: dict[str, object] = {
        "configured": configured(provider),
        "model": model_for(provider),
        "reachable": None,
        "model_installed": None,
    }
    if provider not in {"ollama", "gemma"}:
        return status
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
        installed = [item["name"] for item in response.json().get("models", [])]
        expected = model_for(provider)
        status["reachable"] = True
        status["model_installed"] = any(name == expected or name.startswith(f"{expected}:") for name in installed)
        status["installed_models"] = installed
    except Exception as error:
        status["reachable"] = False
        status["model_installed"] = False
        status["error"] = f"{type(error).__name__}: {error}"
    return status


def openai_agent(prompt: str, schema: type[T]) -> T:
    from openai import OpenAI

    # 요청마다 Client를 열고 닫아 이미 종료된 HTTP Client가 재사용되지 않게 합니다.
    with OpenAI(api_key=settings.openai_api_key) as client:
        response = client.responses.parse(
            model=settings.openai_model,
            input=prompt,
            text_format=schema,
        )
    if response.output_parsed is None:
        raise RuntimeError("GPT가 구조화된 결과를 반환하지 않았습니다.")
    return response.output_parsed


def gemini_agent(prompt: str, schema: type[T]) -> T:
    from google import genai

    # 요청마다 Client 생명주기를 명확히 관리하여 닫힌 Client가 재사용되지 않게 합니다.
    with genai.Client(api_key=settings.gemini_api_key) as client:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config={"response_mime_type": "application/json", "response_json_schema": schema.model_json_schema()},
        )
    if not response.text:
        raise RuntimeError("Gemini가 구조화된 결과를 반환하지 않았습니다.")
    return schema.model_validate_json(response.text)


async def ollama_agent(prompt: str, schema: type[T], model: str) -> T:
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/chat",
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "format": schema.model_json_schema(), "stream": False},
        )
        response.raise_for_status()
        return schema.model_validate_json(response.json()["message"]["content"])


async def generate_structured(provider: str, prompt: str, schema: type[T]) -> tuple[T, dict[str, object]]:
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"지원하지 않는 Provider입니다: {provider}")
    if provider in {"openai", "gemini"} and not configured(provider):
        raise RuntimeError(f"{provider} API Key가 설정되지 않았습니다.")
    started = perf_counter()
    try:
        if provider == "openai":
            result = await asyncio.to_thread(openai_agent, prompt, schema)
        elif provider == "gemini":
            result = await asyncio.to_thread(gemini_agent, prompt, schema)
        else:
            result = await ollama_agent(prompt, schema, model_for(provider))
    except ProviderExecutionError:
        raise
    except Exception as error:
        raise normalize_provider_error(provider, error) from None
    return result, {
        "provider_requested": provider,
        "provider_used": provider,
        "model": model_for(provider),
        "latency_ms": round((perf_counter() - started) * 1000, 2),
        "fallback_used": False,
    }
