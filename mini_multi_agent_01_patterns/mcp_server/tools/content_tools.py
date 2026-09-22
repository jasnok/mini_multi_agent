"""콘텐츠 시나리오의 사실 조회·필수 문구 검사 Tool."""
from mcp_server.database import knowledge_queries as knowledge


def search_facts(topic: str) -> dict:
    """콘텐츠 작성용 사실을 조회합니다."""
    facts = knowledge.find_content_facts(topic)
    return {"success": bool(facts), "topic": topic, "facts": facts, "source": "postgresql"}


def check_required_terms(text: str, scenario: str = "content") -> dict:
    """콘텐츠의 필수 문구를 검사합니다."""
    requirements = knowledge.find_requirements(scenario)
    keywords = {
        "source_confirmation": ("출처",),
        "user_approval": ("사용자 승인", "승인"),
        "validation_boundary": ("경계", "입력 검증"),
        "error_contract": ("오류", "에러"),
        "tests": ("테스트",),
    }
    missing = [
        item["requirement_text"] for item in requirements
        if not any(word in text for word in keywords.get(item["requirement_key"], (item["requirement_text"],)))
    ]
    return {"success": not missing, "scenario": scenario, "missing": missing, "requirements": requirements, "source": "postgresql"}


def get_quality_requirements(scenario: str) -> dict:
    """콘텐츠 또는 코드 작업의 검증 가능한 완료 조건을 조회합니다."""
    requirements = knowledge.find_requirements(scenario)
    return {"success": bool(requirements), "scenario": scenario, "requirements": requirements, "source": "postgresql"}
