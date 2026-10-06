"""세션별 임시 재사용: 성공한 계약만 저장하며 주소·원문은 외부 캐시에 공유하지 않는다."""
import hashlib
import json
from copy import deepcopy

from app.core.config import settings
from app.storage.redis_store import client
from app.orchestration.moving_domains import DOMAIN_AGENTS, DOMAIN_IDS

CONTRACT_VERSION = "moving-v3"


def input_hash(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def cache_key(token):
    return "mini03:moving-session:" + hashlib.sha256(token.encode()).hexdigest()


def load_cached(token):
    if not token:
        return None
    try:
        with client() as redis:
            if redis.exists(cache_key(token) + ":deleted"):
                return None
            raw = redis.get(cache_key(token))
        entry = json.loads(raw) if raw else None
        return entry if entry and entry.get("contract_version") == CONTRACT_VERSION else None
    except Exception:
        return None  # 캐시 장애는 정상 생성 경로를 막지 않는다.


def save_cached(token, state):
    if not token:
        return False
    entry = {"contract_version": CONTRACT_VERSION, "input_hash": input_hash(state["input"]),
             "state": deepcopy(state)}
    try:
        with client() as redis:
            if redis.exists(cache_key(token) + ":deleted"):
                return False
            redis.setex(cache_key(token), settings.run_ttl_seconds, json.dumps(entry, ensure_ascii=False))
        return True
    except Exception:
        return False


def affected_workers(previous, current):
    """원문 변경은 재계획. 기본 조건 변경은 보수적으로 네 Worker를 재생성한다."""
    if previous.get("additional_notes") != current.get("additional_notes"):
        return None
    if any(previous.get(key) != current.get(key) for key in ("origin", "destination", "moving_date", "moving_type")):
        return set(DOMAIN_AGENTS.values())
    changed = set()
    old_answers, answers = previous.get("clarifications", {}), current.get("clarifications", {})
    for key in old_answers.keys() | answers.keys():
        if old_answers.get(key) != answers.get(key):
            changed.add(next(agent for domain, agent in DOMAIN_AGENTS.items() if key in DOMAIN_IDS[domain]))
    for agent in DOMAIN_AGENTS.values():
        if previous.get("worker_providers", {}).get(agent, "openai") != current.get("worker_providers", {}).get(agent, "openai"):
            changed.add(agent)
    if previous.get("item_plans", []) != current.get("item_plans", []):
        before = {item["name"]: item for item in previous.get("item_plans", [])}
        after = {item["name"]: item for item in current.get("item_plans", [])}
        domains = set()
        for name in before.keys() | after.keys():
            old, new = before.get(name), after.get(name)
            if old == new:
                continue
            variants = [item for item in (old, new) if item]
            domains.add("packing")
            if any(item["disposition"] in {"sell", "dispose", "undecided"} for item in variants):
                domains.add("disposal")
            if any(word in name for word in ("냉장고", "세탁기", "에어컨", "가스레인지")) or any(item.get("professional_work") for item in variants):
                domains.add("services")
        changed.update(DOMAIN_AGENTS[domain] for domain in domains)
    return changed


def effective_items(state):
    """사용자가 확인한 입력으로 같은 이름의 추출 결과를 대체한다."""
    extracted = state["outputs"]["move_notes_agent"].get("item_plans", [])
    by_name = {item["name"]: {key: value for key, value in item.items() if key != "evidence"} for item in extracted}
    by_name.update({item["name"]: item for item in state.get("input", {}).get("item_plans", [])})
    return list(by_name.values())


def progress_key(token):
    return cache_key(token) + ":progress"


def save_progress(token, expected_hash, completed_ids):
    cached = load_cached(token)
    if not cached or cached["input_hash"] != expected_hash:
        raise ValueError("목록이 변경되었거나 임시 저장 기간이 지났습니다. 다시 생성하세요.")
    valid = {item["item_id"] for agent in DOMAIN_AGENTS.values() for item in cached["state"]["outputs"][agent]["items"]
             if item.get("applicability", "needs_confirmation") != "not_applicable"}
    if len(completed_ids) != len(set(completed_ids)) or set(completed_ids) - valid:
        raise ValueError("목록에 없는 항목이나 중복 완료 표시입니다.")
    data = {"input_hash": expected_hash, "completed_ids": completed_ids}
    with client() as redis:
        redis.setex(progress_key(token), settings.run_ttl_seconds, json.dumps(data))
    return data


def load_progress(token):
    with client() as redis:
        raw = redis.get(progress_key(token))
    return json.loads(raw) if raw else {"completed_ids": []}


def delete_session(token):
    cached = load_cached(token)
    keys = [cache_key(token), progress_key(token)]
    if cached:
        for run_id in cached["state"].get("session_run_ids", []):
            keys.extend([f"mini03:run:{run_id}", f"mini03:run:{run_id}:events"])
    with client() as redis:
        # 삭제 직전 시작한 요청이 같은 세션 캐시를 다시 저장하지 못하게 한다.
        with redis.pipeline() as pipe:
            pipe.setex(cache_key(token) + ":deleted", settings.run_ttl_seconds, "1")
            pipe.delete(*keys)
            removed = pipe.execute()[-1]
    return {"deleted_keys": removed}


def task_graph(items):
    return [{"task_id": item["item_id"], "owner": next(agent for domain, agent in DOMAIN_AGENTS.items()
             if item["item_id"] in DOMAIN_IDS[domain]),
             "depends_on": item["depends_on"],
             "status": "not_applicable" if item["applicability"] == "not_applicable" else
                       ("needs_confirmation" if item["applicability"] == "needs_confirmation" else "planned")}
            for item in items]
