# Mini Multi-Agent 03 · Supervisor and Router

Rule Router, 실제 LLM Router, Supervisor State와 제한된 Supervisor–Worker Loop를
왼쪽 메뉴에서 단계적으로 실행하는 초보자용 미니 프로젝트입니다.

## 01·02에서 03으로 이어지는 내용

03은 새로운 Pattern을 많이 추가하는 과정이 아닙니다. 01에서 실행한 Router와
Supervisor를 다시 사용하고, 02에서 배운 계약으로 선택 결과를 확인합니다.

```text
01에서 이미 배운 내용                 02에서 이미 배운 내용
Router와 Supervisor Pattern 실행       Agent Role과 Task
Agent와 MCP Tool 실행                  입력·출력 계약과 검증

                         ↓

03에서 새로 배우는 내용
요청을 보고 담당 Worker 하나 선택
완료된 작업을 보고 다음 Worker 선택
허용된 Agent와 실행 순서를 Python으로 확인
```

03에서 꼭 기억할 문장은 두 개입니다.

```text
Router는 Worker를 한 번 선택합니다.
Supervisor는 완료 결과를 보며 다음 Worker를 반복 선택합니다.
```

| 코드 용어 | 쉬운 의미 |
| --- | --- |
| Router | 요청에 맞는 담당 Agent 선택기 |
| Worker | 실제 작업을 수행하는 Agent |
| State | 지금까지 완료된 작업과 결과 |
| Supervisor | State를 보고 다음 Agent를 고르는 Agent |
| Guard | 잘못된 Agent나 실행 순서를 막는 Python 확인 코드 |

```text
Rule Router
→ LLM Router와 선택 Worker
→ Routing 계약
→ State 기반 Supervisor 결정
→ 제한된 Supervisor–Worker Loop
→ Router와 Supervisor 비교
→ Supervisor와 세 Worker 협업
→ 같은 Router를 사내 요청에 적용
→ 장애 대응 계획을 검토 피드백에 따라 수정·재검토
```

## 핵심 구조

```text
Streamlit · 왼쪽 학습 메뉴
→ FastAPI
   ├─ Rule Router
   ├─ Routing Contract Guard
   ├─ GPT Supervisor
   ├─ OpenAI Analyst
   ├─ Llama Developer
   ├─ Gemma Reviewer
   └─ State · Trace · Termination Guard
```

01·02와 같은 구조를 유지하면서 03에서 한 단계를 더 나아갑니다. 핵심 의사결정
Agent와 Workflow는 Python으로 작성하고, 형식이 반복되는 Worker 설정은 YAML로
관리합니다. PostgreSQL의 실제 교육 데이터를 MCP Tool로 조회하며, Redis에는
현재 진행 상태와 실행 Trace를 저장합니다. 별도 Docker Compose를 만들지 않고
기존 `aidevs-postgres`, `aidevs-redis`, `aidevs-ollama` 컨테이너를 함께 사용합니다.

## 디렉터리 구조

```text
backend/app/
├─ agents/
│  ├─ router_agent.py          # 핵심 Agent: Python으로 명시
│  ├─ supervisor_agent.py      # 핵심 Agent: Python으로 명시
│  ├─ definitions/workers.yaml # 반복 Worker 선언
│  ├─ loader.py                # YAML → AgentProfile
│  ├─ registry.py              # Python·YAML Agent 통합 조회
│  └─ runtime.py               # MCP Tool + 실제 LLM 실행
├─ orchestration/engine.py     # 순서, 전이, 반복, 종료 Guard
├─ mcp/client.py
├─ observability/tracker.py    # Redis 진행 상태·Trace
├─ storage/redis_store.py
├─ providers/ · schemas/ · routers/ · services/
frontend/app.py                # 왼쪽 메뉴와 1초 주기 Polling
mcp_server/
├─ main.py
├─ core/config.py
├─ tools/support_tools.py
└─ database/                   # PostgreSQL 연결·SQL·초기화
```

## Python + YAML 적용 기준

YAML은 Agent를 실행하는 프로그램이 아니라 반복되는 **선언 데이터**입니다.

| Python에 유지 | YAML로 이동 |
| --- | --- |
| Router·Supervisor 핵심 지시문 | Worker 이름·목표·설명 |
| 실행 순서와 상태 전이 | Worker별 Provider |
| 최대 반복과 종료 조건 | 출력 계약 이름 |
| Tool 허용 검증과 오류 처리 | 허용 Tool 목록 |

따라서 설정이 늘어나도 Worker를 한눈에 비교할 수 있고, 중요한 실행 정책이 설정
파일에 숨어 버리는 문제를 피할 수 있습니다. 수업에서는
먼저 `definitions/workers.yaml`만 확인합니다. `loader.py`, `registry.py`, `runtime.py`는
Lab 07 실행 구조를 더 살펴보고 싶을 때 읽습니다.

## 왼쪽 메뉴

| 메뉴 | 학습 내용 | 예상 LLM 호출 |
| --- | --- | ---: |
| 01 Rule Router | Keyword 기반 결정적 분류 | 0회 |
| 02 LLM Router | GPT 선택 후 실제 Worker 실행 | 최대 2회 |
| 03 Routing 계약 | Agent Allowlist와 상태 모순 차단, 정보 부족 시 사용자 질문 | 0회 |
| 04 Supervisor 결정 | 현재 State 기반 다음 행동 | 1회 |
| 05 Supervisor–Worker Loop | Analyst·Reviewer 반복과 종료 | 최대 5회 |
| 06 Router vs Supervisor | 적용 상황 비교 | 0회 |
| 07 Supervisor와 세 Worker 협업 | 분석·구현·검토 순차 실행 | 최대 7회 |
| 08 다른 업무에 Router 적용 | 계정·장비·시설 요청 분류 | 1~2회 |
| 09 검토 피드백으로 계획 수정 | 장애 분석·계획·검토·수정 | 최대 11회 |

각 Lab 화면에는 `실행 후 함께 읽을 코드`와 `실행 결과 분석 질문`이 함께 표시됩니다.
학생은 완성된 실행 결과를 먼저 확인한 뒤 Router 선택, MCP Tool 호출, State 갱신과
Python Guard가 구현된 파일을 순서대로 분석합니다.

## 초보자용 진행 순서

| Lab | 먼저 확인할 내용 | 먼저 읽을 코드 |
| --- | --- | --- |
| 01 | Keyword로 담당 Agent 한 명 선택 | `engine.py`의 `rule_router_agent()` |
| 02 | LLM Router가 선택한 Worker만 실행 | `engine.py`의 `llm_router_flow()` |
| 03 | 고객 질문과 Router 결과를 비교해 계약 위반 확인 | `workflow.py`의 `SupportRouteDecision` |
| 04 | 완료된 작업 수에 따라 다음 Agent 선택 | `engine.py`의 `supervisor_decision()` |
| 05 | Supervisor와 Worker 반복 실행 | `engine.py`의 `supervisor_loop()` |
| 06 | Router와 Supervisor 비교 | `catalog.py`의 `ARCHITECTURE_CASES` |
| 07 | Supervisor가 세 Worker를 순서대로 실행 | `definitions/workers.yaml` |
| 08 | 같은 Router 구조를 다른 업무에 재사용 | `internal_flow.py`와 `InternalRouteDecision` |
| 09 | 검토 거절 시 계획 수정 후 재검토 | `incident_plan.py`와 `IncidentReviewResult` |

화면을 먼저 실행하고 표에 적힌 함수나 Class 하나만 읽습니다. 관련 파일 전체를 처음부터
이해하려 하지 않아도 됩니다.

## Router와 Supervisor

| 기준 | Router | Supervisor |
| --- | --- | --- |
| 선택 | 일반적으로 한 번 | 결과를 확인하며 반복 |
| 입력 | 사용자 요청 | 사용자 요청과 현재 State |
| 출력 | 담당 Worker | 다음 Worker 또는 `finish` |
| 적합한 사례 | 배송·환불·기술지원 분류 | 분석→구현→검토 |

Supervisor가 반환한 결과가 계약을 통과해도 현재 단계에서 허용되지 않은 Worker라면
Python이 `invalid_transition`으로 차단합니다.

## 실제 LLM 배정

| 역할 | Provider | Model |
| --- | --- | --- |
| Router·Supervisor Agent | OpenAI | `gpt-4.1-mini` |
| Delivery·Analyst Agent | OpenAI | `gpt-4.1-mini` |
| Technical Support·Developer Agent | Ollama | `llama3.2` |
| Refund·Reviewer Agent | Gemma | `gemma3:1b` |

Llama와 Gemma는 같은 Ollama에서 동시에 실행하지 않고 순차적으로 호출합니다.

## Lab 08 · 다른 업무에 Router 적용

Lab 02의 고객지원 Router를 이해했다면, 같은 실행 순서를 사내 요청에도 적용할 수
있습니다. 새로 배우는 Pattern은 없습니다. **선택 계약과 Worker 역할만 바뀝니다.**

```text
사내 요청
→ OpenAI internal_router_agent가 담당자 선택
   ├─ 계정·권한 → Gemini account_agent
   ├─ 노트북·장비 → Llama equipment_agent
   ├─ 회의실·시설 → Gemma 3 1B facility_agent
   └─ 정보 부족 → 필요한 정보 요청, Worker 실행 안 함
```

실행 순서는 Lab 02와 같습니다.

1. Router가 `InternalRouteDecision` 계약으로 담당자 하나를 선택합니다.
2. Python이 선택 결과를 검사합니다.
3. 선택된 Worker 하나만 `WorkerResult` 계약으로 답합니다.

이 예제는 데이터베이스를 조회하거나 값을 변경하지 않습니다. 새 MCP Tool도 없습니다.
학생은 먼저 화면에서 네 가지 예시를 실행한 뒤 다음 두 파일만 비교하면 됩니다.

- `backend/app/schemas/workflow.py`의 `InternalRouteDecision`
- `backend/app/orchestration/internal_flow.py`의 `run_internal_router_flow()`

Lab 02의 `SupportRouteDecision`, `llm_router_flow()`와 나란히 놓고 보면 재사용되는
구조와 업무마다 달라지는 부분을 쉽게 구분할 수 있습니다.

## Lab 09 · 검토 피드백으로 계획 수정

3층 회의실 프로젝터 화면이 나오지 않는 작은 사례로 점검 안내문을 작성합니다.
`incident_analyst_agent → incident_planner_agent →
incident_reviewer_agent` 순서로 작성합니다. 각 Worker는 YAML에 선언되어 있습니다. 09번의 분석·계획·검토 Agent는 OpenAI를 사용합니다. 각 Agent에는 필요한 정보만 짧게 전달하고,
전체 State와 Trace는 실행 결과에 보관합니다. Python의 `incident_plan.py`가
Supervisor의 제안과 허용 전이를 검증합니다.

Reviewer의 `IncidentReviewResult.approved`가 `false`이면 구체적인 `feedback`을
계획 Agent에게 전달합니다. 계획 Agent는 수정본의 `addressed_feedback`에 반영한
항목을 기록하고 Reviewer가 새 revision을 재검토합니다. 수정은 최대 한 번이며,
두 번째 검토도 승인되지 않으면 `needs_attention`으로 종료합니다. 승인되면
Supervisor가 `finish`를 선택합니다. Provider 또는 계약 실패도 Trace에 그대로 남습니다.

화면의 `첫 검토 거절 → 계획 수정 → 재검토 흐름 재현` 옵션은 기본으로 켜져 있습니다.
이 교육용 옵션에서는 revision 0의 Reviewer가 `영향 범위 확인 단계를 추가하세요.`라는
피드백으로 첫 계획을 거절합니다. revision 1에서는 평소 검토 기준으로 돌아가므로,
피드백이 반영됐다면 승인하고 빠졌다면 다시 거절합니다. 옵션을 끄면 첫 검토부터
Reviewer가 계획 내용만 보고 자유롭게 승인 여부를 결정합니다.

화면은 `POST /api/async-runs/incident-plan`으로 시작하고
`GET /api/async-runs/{run_id}/snapshot`을 Polling합니다. 실제 장애 조치나
시스템 변경은 실행하지 않습니다.

## 환경 준비

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_03_supervisor_router
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 실제 Provider를 설정합니다.

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
GEMMA_MODEL=gemma3:1b
MCP_HOST=127.0.0.1
MCP_PORT=8010
MCP_URL=http://127.0.0.1:8010/mcp
DATABASE_URL=postgresql://agent_user:agent_pwd@127.0.0.1:5433/agent_db
REDIS_URL=redis://127.0.0.1:6379/0
RUN_TTL_SECONDS=3600
API_BASE_URL=http://127.0.0.1:8000
```

## Ollama 확인

```powershell
docker ps --filter "name=aidevs-ollama"
docker exec aidevs-ollama ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

## 데이터베이스 초기화

기존 PostgreSQL 컨테이너가 실행 중인 상태에서 최초 한 번 실행합니다.

```powershell
python -m mcp_server.database.init_db
```

`mini_multi_agent_03` Schema에 주문, 환불 정책, 기술지원 문서가 생성됩니다.

## 세 Process 실행

미니 프로젝트 01~05는 Backend `8000`, MCP `8010`을 공통 사용하므로 한 번에 하나의
프로젝트만 실행합니다.

터미널 1 · MCP Server:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_03_supervisor_router\mcp_server
..\.venv\Scripts\Activate.ps1
python main.py
```

터미널 2 · FastAPI Backend:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_03_supervisor_router
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000 --app-dir backend
```

터미널 3 · Streamlit Frontend:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_03_supervisor_router
.\.venv\Scripts\Activate.ps1
streamlit run .\frontend\app.py --server.port 8530
```

- 화면: `http://127.0.0.1:8530`
- API 문서: `http://127.0.0.1:8000/docs`
- MCP: `http://127.0.0.1:8010/mcp`

실행 버튼을 누르면 Backend가 작업 ID를 먼저 반환합니다. 화면은 1초마다 상태를
조회하여 Progress Bar, 현재 Agent, 현재 단계와 Redis Stream 실행 이력을 갱신합니다.
상태와 실행 이력은 `mini03:run:{run_id}`와 `mini03:run:{run_id}:events`에 저장되며,
`RUN_TTL_SECONDS`(기본 1시간)가 지나면 만료됩니다.

## 환경 진단

Backend 실행 후 다음 명령으로 설정된 Provider와 Backend 상태를 확인합니다.

```powershell
python .\check_environment.py
```

하나라도 실패하면 진단 명령은 종료 코드 `1`을 반환합니다. 코드 변경 후 외부 서비스 없이
실행 가능한 회귀 테스트는 다음과 같이 확인합니다.

```powershell
python -m unittest discover -s tests -v
```

## 주요 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| GET | `/api/labs` | 8개 Lab 정보 |
| GET | `/api/rule-router` | Rule Router 사례 실행 |
| GET | `/api/routing-validation-cases` | 계약 위반 사례 |
| POST | `/api/routing/validate` | Routing 계약 검증 |
| GET | `/api/architecture-cases` | Router·Supervisor 비교 |
| GET | `/api/providers` | Provider 준비 상태 |
| GET | `/api/agents` | Python·YAML Agent Registry |
| GET | `/api/mcp-status` | 실제 MCP Tool 연결 상태 |
| POST | `/api/runs/router` | 실제 Router와 선택 Worker |
| POST | `/api/runs/supervisor-decision` | State 기반 단일 결정 |
| POST | `/api/runs/supervisor-loop` | 최대 5회 Loop |
| POST | `/api/runs/multi-llm-team` | Supervisor와 세 Worker, 최대 7회 호출 |
| POST | `/api/runs/internal-router` | 사내 요청 Router와 선택 Worker |
| POST | `/api/async-runs/{flow_name}` | Polling용 비동기 실행 생성 |
| GET | `/api/async-runs/{run_id}/snapshot` | Redis 상태와 Trace 조회 |

## Python Guard

Supervisor Loop에서 Python이 다음 조건을 최종 통제합니다.

- 허용된 Worker 순서
- 이미 완료된 Worker의 중복 실행
- Worker 계약 검증 성공 여부
- Supervisor와 Worker 오류
- 최대 LLM 호출 수
- 모든 Worker 완료 후 `finish`

종료 이유는 `all_workers_completed`, `supervisor_failed`, `worker_failed`,
`invalid_transition`, `duplicate_worker`, `max_llm_calls` 중 하나로 남습니다.


## 오류 처리 원칙

- Provider 실패를 다른 Provider나 고정 답변으로 대체하지 않습니다.
- Router가 실패하면 Worker를 실행하지 않습니다.
- Worker가 실패하면 State에 완료 결과로 추가하지 않습니다.
- 잘못된 Supervisor 전이를 자동 수정하지 않고 차단합니다.
- Provider, Model, 지연 시간, 결과와 오류를 Trace에 보존합니다.
- Gemini `429 RESOURCE_EXHAUSTED`는 `quota_exhausted`와 재시도 가능 시간으로 정규화하고,
  긴 Provider 원문이나 자동 Provider 대체를 사용하지 않습니다.

## 완료 기준

- Router와 Supervisor의 차이를 State와 선택 횟수로 설명할 수 있습니다.
- Rule Router와 LLM Router를 상황에 맞게 선택할 수 있습니다.
- Routing 계약이 허용되지 않은 Agent를 차단하는 것을 확인할 수 있습니다.
- Supervisor State에서 완료 Agent와 검증된 출력을 읽을 수 있습니다.
- 최대 호출과 종료 이유를 Trace에서 확인할 수 있습니다.
- Supervisor와 세 Worker의 역할과 실행 순서를 설명할 수 있습니다.
