"""Lab 10: 이사 조건 → 체크리스트 → 일정의 출력 계약."""

from datetime import date, datetime
import re
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

MovingType = Literal["general", "semi_packing", "full_packing"]
Phase = Literal["before", "moving_day", "after"]


def today_seoul() -> date:
    return datetime.now(ZoneInfo("Asia/Seoul")).date()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MovingItemPlan(Contract):
    name: str = Field(min_length=1, max_length=80)
    disposition: Literal["keep", "sell", "dispose", "undecided"]
    size: str = Field(default="", max_length=80)
    professional_work: bool = False

    @model_validator(mode="after")
    def nonblank_name(self):
        if not self.name.strip():
            raise ValueError("물품 이름을 입력하세요.")
        self.name = self.name.strip()
        return self


class MovingRequest(Contract):
    origin: str = Field(min_length=2, max_length=200)
    destination: str = Field(min_length=2, max_length=200)
    moving_date: date
    moving_type: MovingType
    additional_notes: str = Field(default="", max_length=2000, description="선택 입력: 보유 물품·제약·미확인 사항 등 추가 참고사항")
    item_plans: list[MovingItemPlan] = Field(default_factory=list, max_length=40, description="사용자가 확인한 물품별 처리 방식. 같은 물품의 참고사항보다 우선합니다.")
    clarifications: dict[Literal["building_access", "internet", "gas", "waste_booking", "school", "care"], str] = Field(default_factory=dict, max_length=6, description="미확인 사항에 대한 사용자 답변. 각 답변은 500자 이내")
    worker_providers: dict[Literal["move_packing_agent", "move_disposal_agent", "move_services_agent", "move_housing_agent"], Literal["openai", "gemini", "ollama", "gemma"]] = Field(default_factory=dict)
    parallel_workers: bool = False
    session_key: str | None = Field(default=None, min_length=32, max_length=128, pattern=r"^[A-Za-z0-9_-]+$", exclude=True, repr=False, description="브라우저별 임시 재사용 키. 다른 사람에게 공유하지 마세요.")

    @model_validator(mode="after")
    def validate_input(self):
        if len(self.origin.strip()) < 2 or len(self.destination.strip()) < 2:
            raise ValueError("출발지와 도착지를 입력하세요.")
        if self.moving_date < today_seoul():
            raise ValueError("이사 희망일은 오늘 또는 이후 날짜여야 합니다.")
        names = [item.name for item in self.item_plans]
        if len(names) != len(set(names)):
            raise ValueError("같은 물품을 중복 입력하지 마세요.")
        if any(not answer.strip() or len(answer) > 500 for answer in self.clarifications.values()):
            raise ValueError("확인한 답변은 공백이 아닌 500자 이내여야 합니다.")
        return self


class MovingSupervisorDecision(Contract):
    agent_id: Literal["moving_supervisor_agent"]
    next_agent: Literal["move_notes_agent", "move_packing_agent", "move_disposal_agent", "move_services_agent", "move_housing_agent", "finish", "needs_information"]
    reason: str = Field(min_length=1, max_length=300)
    task: str = Field(min_length=1, max_length=1000, description="선택한 Worker에게 전달할 구체적인 작업 또는 수정 지시. 종료 시 최종 검토 내용")

    @model_validator(mode="after")
    def validate_korean_reason(self):
        if not re.search(r"[가-힣]", self.reason):
            raise ValueError("Supervisor의 reason은 한글 설명을 포함해야 합니다.")
        return self


class MoveScopeResult(Contract):
    agent_id: Literal["move_scope_agent"]
    origin: str
    destination: str
    moving_date: date
    moving_type: MovingType
    additional_notes: str = Field(default="", max_length=2000)
    summary: str = Field(min_length=1, max_length=300)


class MovingNoteFact(Contract):
    category: Literal["keep", "sell", "dispose", "service", "constraint", "household", "priority", "other"]
    detail: str = Field(min_length=1, max_length=300)
    evidence: str = Field(min_length=1, max_length=2000, description="참고사항 원문에서 그대로 인용한 근거")


class ExtractedMovingItem(MovingItemPlan):
    evidence: str = Field(min_length=1, max_length=2000)


class MoveNotesResult(Contract):
    agent_id: Literal["move_notes_agent"]
    source_notes: str = Field(max_length=2000)
    summary: str = Field(min_length=1, max_length=500)
    facts: list[MovingNoteFact] = Field(max_length=40)
    item_plans: list[ExtractedMovingItem] = Field(default_factory=list, max_length=40, description="물품별 원문 근거를 보존한 추출 결과. 사용자 확인 전 제안 데이터")


class MovingSessionRequest(Contract):
    session_key: str = Field(min_length=32, max_length=128, pattern=r"^[A-Za-z0-9_-]+$", repr=False)


class MovingProgressRequest(MovingSessionRequest):
    input_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    completed_ids: list[str] = Field(max_length=40)


class MovingModelProbeRequest(MovingSessionRequest):
    agent_id: Literal["move_packing_agent", "move_disposal_agent", "move_services_agent", "move_housing_agent"]
    provider: Literal["openai", "gemini", "ollama", "gemma"]


class TemplateItem(Contract):
    item_id: str
    title: str
    category: str
    phase: Phase
    days_offset: int = Field(ge=-30, le=14)
    responsibility: Literal["user", "provider", "confirm_with_provider"]
    condition: str
    guidance: str

    @model_validator(mode="after")
    def validate_phase_offset(self):
        if ((self.phase == "before" and self.days_offset >= 0)
                or (self.phase == "moving_day" and self.days_offset != 0)
                or (self.phase == "after" and self.days_offset <= 0)):
            raise ValueError("템플릿의 단계와 날짜 간격이 모순됩니다.")
        return self


class MovingTemplateResult(Contract):
    data_source: Literal["mock"]
    moving_type: MovingType
    notice: str
    items: list[TemplateItem] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def unique_items(self):
        ids = [item.item_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Mock 준비 항목 ID가 중복되었습니다.")
        return self


class ChecklistItem(Contract):
    item_id: str
    action: str = Field(min_length=1, max_length=220)
    applicability: Literal["applicable", "not_applicable", "needs_confirmation"] = "needs_confirmation"
    applicability_evidence: str = Field(default="", max_length=2000, description="해당 없음 판단의 근거인 사용자 참고사항 원문 인용")
    evidence_fact_index: int | None = Field(default=None, ge=0, description="해당 없음 근거의 notes.facts 배열 인덱스. 프로그램이 해당 fact의 검증된 evidence를 원문 그대로 사용한다.")
    depends_on: list[str] = Field(default_factory=list, max_length=10)


class MovingDomainResult(Contract):
    agent_id: Literal["move_packing_agent", "move_disposal_agent", "move_services_agent", "move_housing_agent"]
    domain: Literal["packing", "disposal", "services", "housing"]
    items: list[ChecklistItem] = Field(min_length=1, max_length=30)
    unresolved_questions: list[str] = Field(default_factory=list, max_length=10)


class MovingAssignment(Contract):
    agent_id: Literal["move_packing_agent", "move_disposal_agent", "move_services_agent", "move_housing_agent"]
    task: str = Field(min_length=15, max_length=1000)


class MovingExecutionPlan(Contract):
    agent_id: Literal["moving_supervisor_agent"]
    notes: MoveNotesResult
    assignments: list[MovingAssignment] = Field(min_length=4, max_length=4)
    reason: str = Field(min_length=1, max_length=500)


class MovingFinalReview(Contract):
    agent_id: Literal["moving_supervisor_agent"]
    approved: bool
    reason: str = Field(min_length=1, max_length=500)
    corrections: list[MovingAssignment] = Field(max_length=2)

    @model_validator(mode="after")
    def check_review(self):
        if self.approved and self.corrections:
            raise ValueError("승인 결과에 수정 요청을 함께 넣을 수 없습니다.")
        if not self.approved and not self.corrections:
            raise ValueError("반려 시 구체적인 담당자 수정 요청이 필요합니다.")
        return self


class MoveChecklistResult(Contract):
    agent_id: Literal["move_checklist_agent"]
    items: list[ChecklistItem] = Field(min_length=1, max_length=30)


class TimelineEntry(Contract):
    item_id: str
    phase: Phase


class MoveTimelineResult(Contract):
    agent_id: Literal["move_timeline_agent"]
    entries: list[TimelineEntry] = Field(min_length=1, max_length=30)
    priority_item_ids: list[str] = Field(min_length=1, max_length=3)
    priority_reason: str = Field(min_length=1, max_length=300)
