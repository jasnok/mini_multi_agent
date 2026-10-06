import sys
import copy
import unittest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch
from datetime import timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))
from app.schemas.moving import MovingRequest, today_seoul
from app.orchestration.moving_supervisor import moving_checklist_flow, invalidate_outputs, verify_output
from app.orchestration.moving_domains import DOMAIN_AGENTS, domain_items, enrich_template, required_links
from mcp_server.tools.moving_tools import get_moving_checklist_template


class DomainFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_preview_then_confirmation_reuses_plan(self):
        request, template, responses = self.fixture()
        request = request.model_copy(update={"session_key": "p" * 43})
        saved = {}
        def save(token, state):
            saved[token] = {"state": copy.deepcopy(state)}
            return True
        with patch("app.orchestration.moving_supervisor.load_cached", side_effect=lambda key: saved.get(key)), \
             patch("app.orchestration.moving_supervisor.save_cached", side_effect=save), \
             patch("app.orchestration.moving_supervisor.call_tool", new_callable=AsyncMock, return_value=template), \
             patch("app.orchestration.moving_supervisor.run_profile", new_callable=AsyncMock, side_effect=responses) as model:
            draft = await moving_checklist_flow(request, plan_only=True)
            self.assertEqual(draft["status"], "awaiting_confirmation")
            self.assertEqual(model.await_count, 1)
            final = await moving_checklist_flow(request)
            self.assertEqual(final["status"], "completed")
            self.assertEqual(final["llm_calls"], 5)
            self.assertEqual(model.await_count, 6)

    async def test_model_probe_checks_same_contract_without_changing_cache(self):
        from app.services.moving_model_probe import probe_worker
        from app.schemas.moving import MovingModelProbeRequest
        request, template, responses = self.fixture()
        result, _ = await self.execute(request, template, responses)
        cached = {"state": copy.deepcopy(result["state"])}
        original = copy.deepcopy(cached)
        with patch("app.services.moving_model_probe.load_cached", return_value=cached), \
             patch("app.services.moving_model_probe.run_profile", new_callable=AsyncMock, return_value=responses[3]) as model:
            probe = await probe_worker(MovingModelProbeRequest(session_key="x" * 43, agent_id="move_packing_agent", provider="gemma"))
        self.assertEqual(probe["semantic_validation"], "passed")
        self.assertFalse(probe["changed_checklist"])
        self.assertEqual(model.await_args.args[0].provider, "gemma")
        self.assertEqual(cached, original)

    async def test_parallel_workers_are_staged_and_keep_six_calls(self):
        request, template, responses = self.fixture()
        request = request.model_copy(update={"parallel_workers": True})
        rendezvous = asyncio.Event()
        inflight = set()
        lookup = {response["result"]["agent_id"]: response for response in responses[1:5]}
        async def model(profile, prompt, schema, tracker):
            if schema.__name__ == "MovingExecutionPlan": return responses[0]
            if schema.__name__ == "MovingFinalReview": return responses[5]
            if profile.agent_id in {"move_packing_agent", "move_housing_agent"}:
                inflight.add(profile.agent_id)
                if len(inflight) == 2: rendezvous.set()
                await asyncio.wait_for(rendezvous.wait(), 1)
            return copy.deepcopy(lookup[profile.agent_id])
        with patch("app.orchestration.moving_supervisor.call_tool", new_callable=AsyncMock, return_value=template), \
             patch("app.orchestration.moving_supervisor.run_profile", side_effect=model):
            result = await moving_checklist_flow(request)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["llm_calls"], 6)
        self.assertEqual(len(inflight), 2)
        self.assertTrue(result["state"]["metrics"]["parallel_enabled"])
        self.assertTrue(all(event.get("semantic_validation") == "passed" for event in result["trace"] if event["action"] == "execute"))

    async def test_clarification_and_provider_only_refresh_related_worker(self):
        request, template, responses = self.fixture()
        cached_result, _ = await self.execute(request, template, responses)
        request = request.model_copy(update={"session_key": "c" * 43, "clarifications": {"building_access": "엘리베이터는 오전 9시부터 사용 가능"},
                                            "worker_providers": {"move_housing_agent": "gemini"}})
        with patch("app.orchestration.moving_supervisor.load_cached", return_value={"state": cached_result["state"]}), \
             patch("app.orchestration.moving_supervisor.save_cached", return_value=True):
            result, model = await self.execute(request, template, [responses[4], responses[5]])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["llm_calls"], 2)
        self.assertEqual(model.await_args_list[0].args[0].provider, "gemini")
        self.assertIn("clarifications", model.await_args_list[0].args[1])

    async def test_extracted_item_requires_original_name_and_evidence(self):
        request, template, responses = self.fixture()
        responses[0]["result"]["notes"]["item_plans"] = [{"name": "에어컨", "disposition": "dispose", "size": "", "professional_work": True,
                                                          "evidence": "에어컨은 철거 후 폐기합니다."}]
        result, _ = await self.execute(request, template, responses)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["checklist"]["item_plans"][0]["name"], "에어컨")
        responses[0]["result"]["notes"]["item_plans"][0]["name"] = "없는 책장"
        result, model = await self.execute(request, template, responses)
        self.assertEqual(result["reason"], "planning_failed")
        self.assertEqual(model.await_count, 1)

    def test_progress_and_delete_validate_session_scope(self):
        from unittest.mock import MagicMock
        from app.orchestration.moving_reuse import save_progress, delete_session, input_hash
        request, template, responses = self.fixture()
        saved_state = {"input": request.model_dump(mode="json"), "outputs": {response["result"]["agent_id"]: response["result"] for response in responses[1:5]},
                       "session_run_ids": ["run-owned123"]}
        entry = {"state": saved_state, "input_hash": input_hash(saved_state["input"])}
        redis = MagicMock()
        with patch("app.orchestration.moving_reuse.load_cached", return_value=entry), \
             patch("app.orchestration.moving_reuse.client") as client:
            client.return_value.__enter__.return_value = redis
            with self.assertRaises(ValueError): save_progress("d" * 43, "0" * 64, [])
            with self.assertRaises(ValueError): save_progress("d" * 43, entry["input_hash"], ["unknown"])
            data = save_progress("d" * 43, entry["input_hash"], ["gas"])
            self.assertEqual(data["completed_ids"], ["gas"])
            delete_session("d" * 43)
            deletion = redis.pipeline.return_value.__enter__.return_value.delete
            self.assertIn("mini03:run:run-owned123", deletion.call_args.args)
            self.assertNotIn("*", "".join(deletion.call_args.args))

    async def test_external_references_reject_unlisted_urls(self):
        from app.services.moving_references import check_references, reference_catalog
        with self.assertRaises(ValueError): await check_references(["http://127.0.0.1/"])
        sources = reference_catalog("관악구", "수유동")
        self.assertEqual(len(sources), 3)
        self.assertTrue(all(source["checked_at"] is None for source in sources))

    async def test_session_reuse_and_partial_regeneration(self):
        request, template, responses = self.fixture()
        request = request.model_copy(update={"session_key": "a" * 43})
        cache = {}
        def save(token, state):
            cache[token] = {"state": copy.deepcopy(state)}
            return True
        with patch("app.orchestration.moving_supervisor.load_cached", side_effect=lambda token: cache.get(token)), \
             patch("app.orchestration.moving_supervisor.save_cached", side_effect=save), \
             patch("app.orchestration.moving_supervisor.call_tool", new_callable=AsyncMock, return_value=template), \
             patch("app.orchestration.moving_supervisor.run_profile", new_callable=AsyncMock, side_effect=responses) as run:
            first = await moving_checklist_flow(request)
            repeated = await moving_checklist_flow(request)
            self.assertEqual(first["llm_calls"], 6)
            self.assertEqual(repeated["llm_calls"], 0)
            self.assertEqual(len(repeated["state"]["reuse"]["reused_agents"]), 4)
            self.assertNotIn("session_key", repeated["state"]["input"])
            self.assertEqual(len(repeated["checklist"]["task_graph"]), 31)
            from app.schemas.moving import MovingItemPlan
            changed = request.model_copy(update={"item_plans": [MovingItemPlan(name="침대", disposition="keep", size="퀸")]})
            run.side_effect = [responses[3], responses[5]]
            partial = await moving_checklist_flow(changed)
            self.assertEqual(partial["status"], "completed")
            self.assertEqual(partial["llm_calls"], 2)
            self.assertEqual(len(partial["state"]["reuse"]["reused_agents"]), 3)

    async def test_notes_change_requires_full_planning_and_session_isolation(self):
        request, template, responses = self.fixture()
        request = request.model_copy(update={"session_key": "b" * 43})
        with patch("app.orchestration.moving_supervisor.load_cached", return_value=None), \
             patch("app.orchestration.moving_supervisor.save_cached", return_value=True):
            result, _ = await self.execute(request, template, responses)
        self.assertEqual(result["llm_calls"], 6)
        from app.orchestration.moving_reuse import affected_workers, cache_key
        self.assertIsNone(affected_workers({"additional_notes": "이전"}, {"additional_notes": "변경"}))
        self.assertNotEqual(cache_key("a" * 43), cache_key("b" * 43))

    def test_structured_item_validation_and_links(self):
        from pydantic import ValidationError
        request, _, _ = self.fixture()
        data = request.model_dump(mode="json")
        data["item_plans"] = [{"name": "에어컨", "disposition": "keep"}, {"name": "가스레인지", "disposition": "sell"}]
        request = MovingRequest.model_validate(data)
        self.assertEqual(required_links({"source_notes": request.additional_notes}, request.model_dump()["item_plans"]), ["gas"])
        data["item_plans"].append(data["item_plans"][0])
        with self.assertRaises(ValidationError): MovingRequest.model_validate(data)

    def fixture(self):
        request = MovingRequest(origin="관악푸르지오 2차", destination="수유동 벽산아파트", moving_date=today_seoul()+timedelta(days=9), moving_type="general", additional_notes="가스레인지는 분리 후 판매하고 에어컨은 철거 후 폐기합니다.")
        template = enrich_template(get_moving_checklist_template("general"))
        order = [DOMAIN_AGENTS[domain] for domain in ("services", "disposal", "packing", "housing")]
        plan = {"agent_id": "moving_supervisor_agent", "notes": {"agent_id": "move_notes_agent", "source_notes": request.additional_notes, "summary": "판매·폐기 준비", "facts": []},
                "assignments": [{"agent_id": agent, "task": "검증된 사용자 상황과 전문 작업 선행조건을 반영해 준비 사항을 작성하세요."} for agent in order], "reason": "업무별 담당자를 배정했습니다."}
        responses = [{"result": plan}]
        for agent in order:
            domain = next(domain for domain, owner in DOMAIN_AGENTS.items() if owner == agent)
            items = [{"item_id": item["item_id"], "action": item["guidance"], "depends_on": ["gas", "appliances"] if item["item_id"] == "waste" else []} for item in domain_items(template, domain)]
            responses.append({"result": {"agent_id": agent, "domain": domain, "items": items, "unresolved_questions": []}})
        responses.append({"result": {"agent_id": "moving_supervisor_agent", "approved": True, "reason": "최종 검토 완료", "corrections": []}})
        return request, template, responses

    async def execute(self, request, template, responses):
        with patch("app.orchestration.moving_supervisor.call_tool", autospec=True, return_value=template) as tool, patch("app.orchestration.moving_supervisor.run_profile", new_callable=AsyncMock, side_effect=responses) as run:
            result = await moving_checklist_flow(request)
            tool.assert_awaited_once_with("get_moving_checklist_template", {"moving_type": request.moving_type}, allowed_tools=frozenset({"get_moving_checklist_template"}))
        return result, run

    async def test_success_six_calls_and_service_contract_passed(self):
        request, template, responses = self.fixture()
        result, run = await self.execute(request, template, responses)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["llm_calls"], 6)
        self.assertEqual(len(result["checklist"]["items"]), 31)
        self.assertIn('"move_services_agent":', run.await_args_list[2].args[1])
        self.assertEqual([event["action"] for event in result["trace"]], ["plan", "execute", "execute", "execute", "execute", "review"])

    async def test_contract_failures_stop_at_two_total_repairs(self):
        request, template, responses = self.fixture()
        bad = copy.deepcopy(responses[2])
        next(item for item in bad["result"]["items"] if item["item_id"] == "waste")["depends_on"] = []
        responses[2:] = [bad, copy.deepcopy(bad), copy.deepcopy(bad)]
        result, run = await self.execute(request, template, responses)
        self.assertEqual(result["reason"], "repair_budget_exhausted")
        self.assertEqual(result["state"]["repair_calls"], 2)
        self.assertEqual(run.await_count, 5)

    async def test_final_review_repairs_and_rechecks_within_nine(self):
        request, template, responses = self.fixture()
        approved = copy.deepcopy(responses[-1])
        housing = copy.deepcopy(responses[4])
        responses[-1] = {"result": {"agent_id": "moving_supervisor_agent", "approved": False, "reason": "주거 준비 보완 필요", "corrections": [{"agent_id": "move_housing_agent", "task": "관리사무소에 확인할 엘리베이터와 차량 이용 조건을 구체적으로 보완하세요."}]}}
        responses += [housing, approved]
        result, _ = await self.execute(request, template, responses)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["llm_calls"], 8)
        self.assertEqual(result["state"]["repair_calls"], 1)

    async def test_invalid_assignment_does_not_execute_worker(self):
        request, template, responses = self.fixture()
        responses[0]["result"]["assignments"][0] = copy.deepcopy(responses[0]["result"]["assignments"][1])
        result, run = await self.execute(request, template, responses)
        self.assertEqual(result["reason"], "planning_failed")
        self.assertEqual(run.await_count, 1)

    async def test_two_review_corrections_cap_at_nine_calls(self):
        request, template, responses = self.fixture()
        approved = copy.deepcopy(responses[-1])
        packing, housing = copy.deepcopy(responses[3]), copy.deepcopy(responses[4])
        responses[-1] = {"result": {"agent_id": "moving_supervisor_agent", "approved": False, "reason": "포장과 주거 준비 보완 필요", "corrections": [
            {"agent_id": "move_packing_agent", "task": "물품별 포장 준비 대상과 확인할 작업 담당을 구체적으로 보완하세요."},
            {"agent_id": "move_housing_agent", "task": "관리사무소에 확인할 운반 조건과 이용 가능 시간을 보완하세요."}]}}
        responses.extend([packing, housing, approved])
        result, run = await self.execute(request, template, responses)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["llm_calls"], 9)
        self.assertEqual(run.await_count, 9)
        self.assertEqual(result["state"]["repair_calls"], 2)

    async def test_empty_notes_and_all_moving_types(self):
        for kind in ("general", "semi_packing", "full_packing"):
            request, template, responses = self.fixture()
            request = request.model_copy(update={"moving_type": kind, "additional_notes": ""})
            template["moving_type"] = kind
            responses[0]["result"]["notes"].update(source_notes="", summary="추가 참고사항이 없습니다.", facts=[])
            result, _ = await self.execute(request, template, responses)
            self.assertEqual(result["status"], "completed")

    async def test_final_cycle_repair_without_extra_supervisor_call(self):
        request, template, responses = self.fixture()
        good = copy.deepcopy(responses[4])
        for item in responses[4]["result"]["items"]:
            if item["item_id"] == "home_inspection": item["depends_on"] = ["building_access"]
            if item["item_id"] == "building_access": item["depends_on"] = ["home_inspection"]
        responses.insert(5, good)
        result, _ = await self.execute(request, template, responses)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["llm_calls"], 7)

    async def test_evidence_index_and_dependency_invalidation(self):
        request, template, responses = self.fixture()
        request = request.model_copy(update={"additional_notes": "자녀와 반려동물은 없습니다."})
        state = {"template": template, "outputs": {"move_notes_agent": {"facts": [{"evidence": request.additional_notes}]}}}
        payload = responses[4]["result"]
        school = next(item for item in payload["items"] if item["item_id"] == "school")
        school.update(applicability="not_applicable", applicability_evidence="자녀와 반려동물이 없습니다.", evidence_fact_index=0)
        output = verify_output("move_housing_agent", payload, request, state)
        self.assertEqual(next(item for item in output.items if item.item_id == "school").applicability_evidence, request.additional_notes)
        school["evidence_fact_index"] = 9
        with self.assertRaisesRegex(ValueError, "범위"): verify_output("move_housing_agent", payload, request, state)
        self.assertEqual(required_links({"source_notes": "에어컨은 가져갑니다. 책장은 폐기합니다."}), [])
        state = {"outputs": dict.fromkeys(DOMAIN_AGENTS.values(), {}), "consumed_outputs": {"move_disposal_agent": ["move_services_agent"]}, "completed_agents": []}
        invalidate_outputs(state, "move_services_agent")
        self.assertNotIn("move_disposal_agent", state["outputs"])
        self.assertIn("move_packing_agent", state["outputs"])

    async def test_api_invalid_input(self):
        from fastapi.testclient import TestClient
        from app.main import app
        request, _, _ = self.fixture()
        with TestClient(app) as client:
            for change in ({"origin": " "}, {"moving_type": "invalid"}, {"moving_date": "2020-01-01"}):
                self.assertEqual(client.post("/api/runs/moving-checklist", json={**request.model_dump(mode="json"), **change}).status_code, 422)
