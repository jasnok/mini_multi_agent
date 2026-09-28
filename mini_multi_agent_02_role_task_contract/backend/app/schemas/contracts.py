from typing import Literal

from pydantic import BaseModel, Field, model_validator


ProviderName = Literal["openai", "gemini", "ollama", "gemma"]


class AgentRoleCard(BaseModel):
    agent_id: str
    goal: str
    responsibilities: list[str] = Field(min_length=1, max_length=6)
    non_goals: list[str] = Field(min_length=1, max_length=6)


class AgentTask(BaseModel):
    task_id: str
    agent_id: str
    required_input: list[str]
    expected_output: list[str]
    completion_condition: str


class BudgetAgentInput(BaseModel):
    """Lab 03에서 처음 확인하는 가장 작은 Agent 입력 계약입니다.

    01에서는 자연어 여행 요청을 그대로 Agent에게 전달했습니다. 02에서는 Agent가 실행되기
    전에 꼭 필요한 값과 허용 범위를 Python Model로 표현합니다. 처음부터 모든 여행 조건을
    넣지 않고 목적지, 여행 일수, 총예산 세 필드만 사용합니다.
    """

    destination: str = Field(min_length=1)
    days: int = Field(ge=1, le=30)
    total_budget: int = Field(gt=0)


class BudgetTaskInput(BudgetAgentInput):
    """실행 가능한 예산 Task의 네 필수 입력입니다."""

    people: int = Field(gt=0)


class TaskExecutionRequest(BaseModel):
    task_id: Literal["allocate_budget"]
    inputs: dict[str, object]


class TaskMessageRequest(BaseModel):
    task_id: Literal["allocate_budget"]
    message: str = Field(min_length=1, max_length=1000)
    known_inputs: dict[str, object] = Field(default_factory=dict)


class MultiTaskMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    known_inputs: dict[str, object] = Field(default_factory=dict)


class WeatherResult(BaseModel):
    agent_id: Literal["weather_agent"] = "weather_agent"
    forecast_summary: str
    cautions: list[str] = Field(default_factory=list, max_length=5)
    source_confirmed: bool


class PlaceResult(BaseModel):
    agent_id: Literal["place_agent"] = "place_agent"
    places: list[str] = Field(min_length=1, max_length=6)
    selection_reason: str


class LodgingResultDraft(BaseModel):
    """예약 정보가 아닌 교육용 숙소 유형과 비용 기준입니다."""

    agent_id: Literal["lodging_agent"] = "lodging_agent"
    selected_option: str
    selection_reason: str
    nightly_cost: int = Field(ge=0)
    nights: int = Field(ge=1)
    total_cost: int = Field(ge=0)
    availability_confirmed: bool

class LodgingResult(LodgingResultDraft):
    @model_validator(mode="after")
    def lodging_total_matches(self) -> "LodgingResult":
        if self.total_cost != self.nightly_cost * self.nights:
            raise ValueError("숙박 총액이 1박 비용과 숙박일수의 곱과 다릅니다.")
        return self


class BudgetBreakdown(BaseModel):
    """OpenAI Structured Outputs가 검증할 수 있는 명시적인 예산 항목 계약입니다."""

    transport: int = Field(ge=0, description="전체 교통비")
    lodging: int = Field(ge=0, description="전체 숙박비")
    food: int = Field(ge=0, description="전체 식비")
    reserve: int = Field(ge=0, description="예상하지 못한 지출을 위한 예비비")


class BudgetResultDraft(BaseModel):
    """OpenAI가 작성하는 구조 초안이며 최종 산술 검증 전 단계입니다."""

    agent_id: Literal["budget_agent"] = "budget_agent"
    currency: Literal["KRW"] = "KRW"
    breakdown: BudgetBreakdown
    total: int = Field(ge=0)


class BudgetResult(BudgetResultDraft):
    """MCP 계산값을 적용한 뒤 사용하는 최종 Agent 출력 계약입니다."""

    @model_validator(mode="after")
    def total_must_match_breakdown(self) -> "BudgetResult":
        amounts = self.breakdown.model_dump().values()
        if sum(amounts) != self.total:
            raise ValueError("예산 합계가 항목별 금액의 합과 다릅니다.")
        return self


class SafetyResult(BaseModel):
    agent_id: Literal["safety_agent"] = "safety_agent"
    risks: list[str] = Field(min_length=1, max_length=6)
    required_actions: list[str] = Field(min_length=1, max_length=6)


class ItineraryResult(BaseModel):
    agent_id: Literal["itinerary_agent"] = "itinerary_agent"
    destination: str
    day_plans: list[str] = Field(min_length=1, max_length=30)
    applied_constraints: list[str] = Field(default_factory=list, max_length=10)


class SupportCaseResult(BaseModel):
    """Lab 09에서 고객 문의를 다음 Agent가 사용할 구조로 정리한 결과입니다."""

    agent_id: Literal["support_analyst_agent"] = "support_analyst_agent"
    order_id: str | None = None
    issue: str = Field(min_length=1)
    requested_action: str = Field(min_length=1)
    completed: bool
    missing_information: list[str] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def completion_must_match_information(self) -> "SupportCaseResult":
        if self.completed and (not self.order_id or self.missing_information):
            raise ValueError("완료된 문의 분석에는 order_id가 있고 missing_information이 비어 있어야 합니다.")
        if not self.completed and not self.missing_information:
            raise ValueError("완료되지 않은 문의 분석에는 missing_information이 필요합니다.")
        return self


class SupportResponseResult(BaseModel):
    """검증된 고객 문의 분석만 사용해 작성한 최종 안내 결과입니다."""

    agent_id: Literal["support_writer_agent"] = "support_writer_agent"
    message: str = Field(min_length=1)
    next_actions: list[str] = Field(min_length=1, max_length=5)
    used_order_id: str = Field(min_length=1)


class SpecialistStatus(BaseModel):
    agent_id: Literal["budget_agent"] = "budget_agent"
    summary: str
    missing_information: list[str] = Field(default_factory=list, max_length=5)
    completed: bool


class ValidationRequest(BaseModel):
    contract_name: Literal["BudgetAgentInput", "WeatherResult", "PlaceResult", "LodgingResult", "BudgetResult", "SafetyResult", "ItineraryResult", "SupportCaseResult", "SupportResponseResult"]
    payload: dict[str, object]


class MultiLlmRequest(BaseModel):
    message: str = Field(min_length=3, max_length=1000)


CONTRACTS = {
    "WeatherResult": WeatherResult,
    "PlaceResult": PlaceResult,
    "LodgingResult": LodgingResult,
    "BudgetResult": BudgetResult,
    "SafetyResult": SafetyResult,
    "ItineraryResult": ItineraryResult,
    "SupportCaseResult": SupportCaseResult,
    "SupportResponseResult": SupportResponseResult,
}

# 화면에서 입력 계약과 출력 계약을 같은 검증 API로 실습하기 위한 목록입니다.
# Agent Runtime은 위의 CONTRACTS(출력 계약)만 사용합니다.
VALIDATION_CONTRACTS = {"BudgetAgentInput": BudgetAgentInput, **CONTRACTS}

# 외부 LLM 응답을 먼저 구조화할 때 사용하는 계약입니다. BudgetResult의 합계 불변식은
# MCP 계산값을 적용한 다음 최종 CONTRACTS 검증에서 확인합니다.
LLM_RESPONSE_CONTRACTS = {
    **CONTRACTS,
    "BudgetResult": BudgetResultDraft,
    "LodgingResult": LodgingResultDraft,
}
