from app.orchestration.engine import PatternEngine
from app.providers.registry import SUPPORTED_PROVIDERS
from app.schemas.runs import RunRequest, RunResult, TraceEvent


RUNS: dict[str, RunResult] = {}


async def execute(request: RunRequest) -> RunResult:
    if request.provider_mode != "compare":
        result = await PatternEngine(request).run()
        RUNS[result.run_id] = result
        return result

    comparison = RunResult(
        scenario=request.scenario,
        pattern=request.pattern,
        provider_mode="compare",
        termination_reason="provider_comparison_finished",
    )
    successful = 0
    for provider in SUPPORTED_PROVIDERS:
        child = await PatternEngine(request, provider_override=provider).run()
        comparison.outputs[provider] = child.model_dump()
        comparison.selected_agents.extend(
            agent for agent in child.selected_agents if agent not in comparison.selected_agents
        )
        comparison.trace.append(
            TraceEvent(
                step=len(comparison.trace) + 1,
                actor=f"comparison:{provider}",
                action="provider_run",
                status="completed" if child.status == "completed" else "failed",
                provider=provider,
                details={"child_run_id": child.run_id, "error": child.error},
            )
        )
        successful += child.status == "completed"
    comparison.status = "completed" if successful else "failed"
    comparison.summary = f"4개 LLM 실행 중 {successful}개가 완료됐습니다. 실패 결과도 비교표에 유지합니다."
    if not successful:
        comparison.error = "사용 가능한 Provider가 없습니다. API Key와 Ollama를 확인하세요."
    RUNS[comparison.run_id] = comparison
    return comparison


def find_run(run_id: str) -> RunResult | None:
    return RUNS.get(run_id)
