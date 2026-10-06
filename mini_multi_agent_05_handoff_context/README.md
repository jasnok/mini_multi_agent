# Mini Multi-Agent 05 · Handoff and Context

01~04에서 배운 역할·계약·Supervisor·분산 실행을 바탕으로, Agent 사이의 최소 Context와
업무 책임을 안전하게 이전하는 전체 Handoff 생명주기를 구현합니다.

```text
Open-Meteo MCP
→ OpenAI Weather Agent
→ Handoff 제안
→ YAML 경로 + Python Guard
→ Gemma Itinerary Agent 수락·실행
→ owner_agent 변경
→ Redis Event → SSE 화면
```

## 학습 단계

| Lab | 내용 | 실제 연결 |
| --- | --- | --- |
| 01 | 전체 State에서 최소 Context 선택 | 없음 |
| 02 | Handoff Envelope | 없음 |
| 03 | YAML Policy와 Python Guard | 없음 |
| 04 | 수락 이후 책임 소유권 변경 | 없음 |
| 05 | 거절·중복·사용자·Context 실패 | 없음 |
| 06 | 실제 Weather→Itinerary Handoff | Open-Meteo·OpenAI·Gemma·Redis·SSE |
| 07 | 사내 IT 접수→계정 지원 Handoff | OpenAI·Gemma, DB·MCP 없음 |
| 08 | 라우터가 계정·기기·접근 권한 Agent 중 선택하고 경로별 Handoff 생성 | OpenAI·Gemma, DB·MCP 없음 |
| 09 | 상담→환불 문의의 간단한 Handoff | OpenAI·Gemma, 실제 환불 실행 없음 |

각 Lab 화면에는 생각할 질문의 핵심 답변과 상세 설명, 예상 LLM 호출 수,
`실행 후 먼저 읽을 코드`와 `실행 결과 분석 질문`이 함께 표시됩니다.

## 디렉터리 구조

```text
backend/app/
├─ agents/
│  ├─ weather_agent.py
│  ├─ itinerary_agent.py
│  ├─ it_triage_agent.py
│  ├─ account_support_agent.py
│  ├─ definitions/handoff_policies.yaml
│  ├─ registry.py
│  └─ runtime.py                # 허용 MCP Tool + 실제 LLM 실행
├─ orchestration/
│  ├─ guards.py
│  └─ engine.py
│  └─ internal_flow.py           # 사내 IT Handoff 적용 예제
├─ schemas/contracts.py
├─ mcp/client.py
├─ observability/tracker.py
├─ storage/redis_store.py
├─ providers/registry.py
└─ routers/handoff.py
frontend/app.py
mcp_server/
├─ main.py
├─ core/config.py
└─ tools/weather_tools.py
```

## Python과 YAML의 책임

| Python | YAML |
| --- | --- |
| 사용자·현재 책임자·task/trace 결속 확인 | 허용 `from_agent → to_agent` 경로 |
| 중복 Handoff 차단 | 필수·선택 Context Key |
| 중첩 민감정보·필수 값·누적 Hop 검증 | 경로별 최대 Hop |
| 대상 성공 이후 owner 변경 | 반복 가능한 경로 선언 |

YAML은 정책 선언이며 실행 코드가 아닙니다. 보안과 상태 변경은 Python이 최종 통제합니다.

## Redis와 SSE

- `mini05:run:{run_id}`: 최신 Handoff Snapshot
- `mini05:run:{run_id}:events`: Handoff Event Stream
- SSE: Event를 발생 즉시 Streamlit에 전달
- Snapshot API: 새로고침·재연결 이후 현재 책임자와 상태 복구
- 상태와 Event는 `RUN_TTL_SECONDS`(기본 3600초) 후 만료

주요 Event:

```text
handoff_workflow_started
→ tool_completed
→ handoff_proposed
→ handoff_validated
→ ownership_transferred
→ target_agent_completed 또는 handoff_failed
```

## 환경 준비

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_05_handoff_context
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 `OPENAI_API_KEY`와 `GEMINI_API_KEY`를 설정합니다. Gemma 3 1B는 기존 `aidevs-ollama`, Redis는 기존
`aidevs-redis` 컨테이너를 사용합니다. 별도 Docker Compose는 만들지 않습니다.

```dotenv
GEMMA_MODEL=gemma3:1b
```

## 세 Process 실행

미니 프로젝트 01~05는 Backend `8000`, MCP `8010`을 공통 사용하므로 한 번에 하나의
프로젝트만 실행합니다.

터미널 1 · MCP Server:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_05_handoff_context\mcp_server
..\.venv\Scripts\Activate.ps1
python main.py
```

터미널 2 · Backend:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_05_handoff_context
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000 --app-dir backend
```

터미널 3 · Frontend:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_05_handoff_context
.\.venv\Scripts\Activate.ps1
streamlit run .\frontend\app.py --server.port 8550
```

- 화면: `http://127.0.0.1:8550`
- API 문서: `http://127.0.0.1:8000/docs`
- MCP: `http://127.0.0.1:8010/mcp`

## 주요 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| GET | `/api/labs` | 9개 학습 단계 |
| GET | `/api/minimum-context` | 최소 Context 비교 |
| GET | `/api/registry` | Python Agent와 YAML 경로 |
| GET | `/api/guard-cases` | 차단 사례 |
| GET | `/api/mcp-status` | Open-Meteo MCP Tool |
| POST | `/api/runs/handoff` | 실제 Handoff 실행 생성 |
| POST | `/api/runs/internal-handoff` | 사내 IT 접수→계정 지원 Handoff |
| POST | `/api/runs/routed-handoff` | 사내 IT 요청을 세 전문 Agent 중 하나로 Handoff |
| POST | `/api/runs/refund-handoff` | 상담→환불 문의 Handoff |
| GET | `/api/runs/{run_id}/events` | SSE Handoff Event |
| GET | `/api/runs/{run_id}/snapshot` | Redis 최신 상태 |

## Lab 07 · 다른 업무에 Handoff 적용

03에서 사내 요청 Router는 담당 Worker를 골랐습니다. 05의 Handoff는 첫 Agent가 이미
요청을 접수한 상태에서 전문 Agent에게 **업무 책임과 최소 Context를 함께 넘깁니다.**

```text
사내 계정 요청
→ OpenAI it_triage_agent가 접수하고 Handoff 제안
→ Python이 경로·현재 책임자·최소 Context 확인
→ Gemma 3 1B account_support_agent가 계정 확인 절차 작성
→ 성공한 뒤 owner_agent 변경
```

전달하는 Context는 직원 ID, 시스템 이름, 문제 내용뿐입니다. 전체 대화,
비밀번호, API Key와 내부 Prompt는 전달하지 않습니다. 이 예제에는 데이터베이스와
MCP Tool을 추가하지 않았으므로 학생은 다음 두 파일을 중심으로 읽습니다.

- `backend/app/orchestration/internal_flow.py`의 `run_internal_handoff()`
- `backend/app/agents/definitions/handoff_policies.yaml`의 `it_triage_to_account_support`

여행 예제와 사내 IT 예제를 비교하면서 업무마다 바뀌는 Agent·Context와 그대로
유지되는 제안→검증→실행→책임 이전 순서를 구분할 수 있습니다.

## 완료 기준

- 함수 호출과 책임 Handoff의 차이를 설명할 수 있습니다.
- 최소 Context와 Handoff Envelope를 구성할 수 있습니다.
- YAML 경로 정책과 Python Guard의 책임을 구분할 수 있습니다.
- 수락 전후 `owner_agent` 변화를 설명할 수 있습니다.
- 실제 OpenAI→Gemma Handoff Event를 SSE 화면에서 확인할 수 있습니다.
- 사내 IT Handoff에서도 같은 책임 이전 순서를 설명할 수 있습니다.
- 실패 시 원래 책임자가 유지되는 것을 Snapshot에서 확인할 수 있습니다.

## 검증

환경 진단은 실제 실행 경로인 OpenAI와 Gemma, Redis, 05 Backend와 MCP Tool 1개를
검사하며 하나라도 실패하면 종료 코드 `1`을 반환합니다.

```powershell
python -m unittest discover -s tests -v
python .\check_environment.py
```

Gemini `429 RESOURCE_EXHAUSTED`는 `quota_exhausted`와 재시도 가능 시간으로 정규화하며,
다른 Provider로 자동 대체하지 않습니다.

## Lab 08 · 라우터가 선택하는 세 가지 Handoff

사내 지원 라우터(OpenAI)는 `RoutedSupportDecision` Output Contract로 대상 Agent, 선택 이유와 넘길 책임을 정합니다.
Python은 해당 YAML 경로에 필요한 Context만 골라 `HandoffEnvelope`를 만들고 Guard로 검증합니다.

| 라우터의 선택 | 필수 Context | 대상 Output Contract |
| --- | --- | --- |
| 계정 지원 | `employee_id`, `system_name`, `issue` | `AccountSupportResult` |
| 기기 지원 | `employee_id`, `issue` | `DeviceSupportResult` |
| 접근 권한 지원 | `employee_id`, `system_name`, `issue` | `AccessSupportResult` |

08번 화면에서 경로별 필수 Context를 비교하고 예시 요청을 실행하면
라우터 판단, 생성한 Envelope, Guard 결과, 검증 후 전달 내용, 대상 Agent 결과와 책임 이전을 순서대로 볼 수 있습니다.
선택된 경로에 필수 값이 없으면 대상 Agent는 실행되지 않고 라우터가 책임을 유지합니다.

## Lab 09 · 간단한 환불 문의 Handoff

상담 Agent가 `SupportRefundDecision` Output Contract로 인계 이유·책임·주문번호·문의 내용을 반환합니다.
그 결과로 `HandoffEnvelope`를 만들고 Guard가 필요한 Context와 경로를 확인합니다.
환불 Agent가 `RefundHandoffResult`로 다음 확인 절차를 반환하면 문의 책임자가 환불 Agent로 바뀝니다.
실제 주문 조회나 환불 지급은 실행하지 않습니다.
