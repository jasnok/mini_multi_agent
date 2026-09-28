# Mini Multi-Agent 02 · Role, Task and Contract

Agent의 역할·Task·입출력 계약과 검증된 결과 전달을 실제 LLM, MCP, PostgreSQL, Redis로
학습하는 프로젝트입니다. Mock 응답과 JSON Data Source fallback은 사용하지 않습니다.

## 01에서 02로 이어지는 내용

01에서는 Single Agent와 Multi-Agent를 비교하고 여러 실행 Pattern을 직접 실행했습니다.
02에서는 새로운 Pattern을 추가하지 않습니다. 01에서 사용한 여행 Agent에 책임과 계약을
하나씩 붙여서, Agent 사이의 경계를 코드로 표현하는 방법만 추가합니다.

```text
01에서 이미 배운 내용                 02에서 새로 추가하는 내용
여러 Agent를 역할별로 나누기           Role에 책임과 Non-goal 적기
Agent가 Tool을 사용해 결과 만들기       Task에 입력·출력·완료 조건 적기
자연어 요청을 Agent에게 전달하기        입력값을 Pydantic 계약으로 먼저 확인하기
여러 Agent 결과와 Trace 확인하기        역할별 출력 계약을 검증하기
Sequential Pattern 실행하기             검증된 결과만 다음 Agent에 전달하기
```

02의 핵심 질문은 네 가지입니다.

1. 이 Agent가 해야 할 일과 하지 말아야 할 일은 무엇인가?
2. 이 Task를 시작하려면 어떤 입력이 필요한가?
3. Agent는 어떤 구조의 결과를 반환해야 하는가?
4. 검증에 실패한 결과를 다음 Agent에게 전달해도 되는가?

처음부터 모든 여행 조건을 하나의 계약에 넣지 않습니다. Lab 03에서는 목적지, 여행 일수,
총예산만 가진 작은 `BudgetAgentInput`부터 시작합니다.

## 핵심 구조

```text
Streamlit :8501
  → FastAPI :8000
    ├─ Role·Task·Pydantic Contract API
    ├─ Background Agent 실행
    └─ Redis Snapshot·Stream
       ├─ 현재 진행 상태
       └─ 시간순 Trace Event
    → HTTP MCP :8010
       ├─ Open-Meteo 실제 날씨
       └─ PostgreSQL 장소·예산 기준
```

- Weather Agent: Open-Meteo → `WeatherResult`
- Place Agent: PostgreSQL → `PlaceResult`
- Budget Agent: PostgreSQL 기준 + 결정적 계산 → `BudgetResult`
- Safety Agent: 사용자가 명시한 제약 → `SafetyResult`
- Itinerary Agent: 검증된 이전 Context → `ItineraryResult`

외부 API·DB·Provider가 실패하면 가상 결과로 대체하지 않고 실패 Trace를 남깁니다.

## Lab 01~11

| Lab | 학습 내용 | Backend API |
| --- | --- | --- |
| 01 | Goal·Responsibilities·Non-goals로 Role 정의 | `GET /api/role-cards` |
| 02 | 다섯 Agent의 필수 입력·출력·완료 조건으로 Task 분할 | `GET /api/tasks` |
| 03 | 목적지·여행 일수·총예산 입력 계약과 경계값 | `POST /api/contracts/validate` |
| 04 | 역할별 Pydantic 출력 계약 | `GET /api/contracts` |
| 05 | 필드·역할·합계 불변식 검증 | `GET /api/validation-cases`, `POST /api/contracts/validate` |
| 06 | 완료·정보 부족·실행 실패 구분 | `GET /api/incomplete-states` |
| 07 | 네 LLM의 역할별 계약 실행 | 비동기 실행 + Snapshot 조회 |
| 08 | 검증된 Budget만 Itinerary에 전달 | 비동기 실행 + Snapshot 조회 |
| 09 | 같은 계약 구조를 고객지원 업무에 적용 | 비동기 실행 + Snapshot 조회 |
| 10 | `AgentTask` 명세를 예산 Agent 실행에 연결 | `GET /api/tasks`, `POST /api/tasks/execute` |
| 11 | 날씨에 따라 장소·숙소·예산을 순차 검증 | `POST /api/tasks/execute-multi-from-message` |

개념 화면(01~06)은 대표 예시 또는 검증 사례를 보여 줍니다. 실제 요청을 보내는
07~09에는 선택 가능한 요청 예시가 있으며, 10에서는 Task 입력 JSON을 직접 수정합니다.
11에서는 사용자 요청을 문장으로 입력하고 부족한 값에 답합니다.

각 화면의 `실행 후 함께 읽을 코드`를 열면 해당 결과를 만드는 Backend, MCP Server,
Orchestration 파일을 바로 확인할 수 있습니다. 예제 코드는 일부러 미완성 상태로 두지
않으며, 정상 결과와 계약이 정상적으로 차단한 결과를 실행한 뒤 코드 흐름을 분석합니다.

## 초보자용 코드 읽기 순서

화면을 먼저 실행하고 아래 파일을 한 번에 하나씩 읽습니다.

| Lab | 먼저 읽을 파일 | 찾을 내용 |
| --- | --- | --- |
| 01 | `backend/app/services/catalog.py` | Goal, Responsibilities, Non-goals |
| 02 | `backend/app/tasks/registry.py`와 각 `*_task.py` | required_input, expected_output, completion_condition |
| 03 | `backend/app/schemas/contracts.py` | `BudgetAgentInput`의 세 필드와 범위 |
| 04 | `backend/app/schemas/contracts.py` | Weather와 Budget 출력 필드의 차이 |
| 05 | `backend/app/services/contract_service.py` | 어떤 Pydantic 계약으로 검증하는가 |
| 06 | `backend/app/services/catalog.py` | 완료·정보 부족·실행 실패의 차이 |
| 07 | `backend/app/agents/runtime.py` | Tool → LLM → 출력 계약 검증 순서 |
| 08 | `backend/app/orchestration/verified_flow.py` | Budget 검증 실패 시 Itinerary를 건너뛰는 분기 |
| 09 | `backend/app/orchestration/support_flow.py` | 고객 문의 분석 검증 후 답변 Agent 실행 또는 Skip |
| 10 | `backend/app/orchestration/task_execution.py` | `AgentTask` 명세를 입력 확인·Agent 실행·완료 판정에 연결 |
| 11 | `backend/app/orchestration/weather_place_lodging_budget.py` | 자유 문장 입력 후 날씨·장소·숙소·예산 순차 검증 |

Lab 07 요청은 쉬운 순서로 실행합니다.

1. `1명·60만 원` 정상 요청
2. 정상 요청에 `해산물 알레르기` 조건 추가
3. `3명·80만 원` 예산 부족 요청

세 번째 요청은 시스템 고장이 아니라, 기존 PostgreSQL 비용 기준으로 필요한 금액이
총예산보다 커서 Budget Agent가 정상적으로 실패를 반환하는 예제입니다.

## Lab 09 · 다른 업무에 같은 구조 적용

01~08은 여행 업무로 Role, Task, Contract와 검증된 전달을 확인했습니다. 09에서는 새로운
Pattern이나 DB를 추가하지 않고 같은 설계 순서를 고객지원 업무에 적용합니다.

```text
고객 문의
→ OpenAI 고객 문의 분석 Agent
→ SupportCaseResult 계약 검증
├─ 주문번호 있음 → Gemma 3 1B 답변 작성 Agent
└─ 주문번호 없음 → 추가 정보 요청, 답변 작성 Agent Skip
```

| Agent | 책임 | 하지 않는 일 |
| --- | --- | --- |
| `support_analyst_agent` | 주문번호·문제·요청 행동 구조화 | 실제 주문 상태 추측, 고객 답변 작성 |
| `support_writer_agent` | 검증된 분석으로 확인 행동 안내 | 배송 상태·환불 가능 여부 확정 |

09는 03의 Router와 다릅니다. 담당 Agent를 동적으로 선택하지 않고 다음 고정 순서에서
검증된 결과 전달만 확인합니다.

```text
02 Lab 09: Support Analyst → Contract Guard → Support Writer
03: Router → Delivery/Refund/Technical Support 중 하나 선택
```

새로운 주문 Table이나 MCP Tool을 만들지 않은 이유는 이 Lab의 목적이 실제 주문 조회가
아니라, 도메인이 바뀌어도 계약 설계 순서가 유지되는지 확인하는 것이기 때문입니다.


## AgentTask 정의 위치

`AgentTask` 모델은 `backend/app/schemas/contracts.py`에 있습니다. 각 Task의 실제
설정은 `backend/app/tasks/` 아래 `weather_task.py`, `place_task.py`,
`budget_task.py`, `safety_task.py`, `itinerary_task.py`에 하나씩 정의합니다.
`tasks/registry.py`가 이를 모아 `TASKS`와 `TASK_BY_ID`를 제공합니다.
`GET /api/tasks` 화면과 10·11 실행 코드가 같은 Registry를 읽으므로 학습용 목록과
실행 Task 명세가 따로 어긋나지 않습니다. `completion_condition`은 설명 문장이고,
실제 검증은 Orchestration의 Python 코드가 담당합니다.

## Lab 10 · AgentTask를 실제 실행에 연결

02 화면의 `AgentTask`는 설계 명세입니다. 10에서는 `allocate_budget` Task 하나를
실행 코드에 연결합니다. 입력 JSON에서 `people`을 지우면 `required_input` 확인 단계에서
멈추므로 LLM을 호출하지 않습니다. 입력이 완전하면 `task.agent_id`로 Budget Agent를
찾아 실행하고, `expected_output` 필드와 `BudgetResult` 계약을 검증합니다. 마지막으로
출력 총액이 요청 예산과 같은지 Python 규칙으로 확인합니다.

`completion_condition` 문장은 사람을 위한 설명입니다. 임의의 문자열을 실행하지 않고
명시적인 검증 코드로 연결합니다. 정상 입력은 MCP 비용 기준과 OpenAI를 호출하며,
Provider나 Tool 실패는 그대로 실패 결과에 남습니다.

## Lab 11 · 날씨 → 장소 → 숙소 → 예산

사용자가 “부산 2박 3일 여행, 예산 60만 원”이라고 쓰면 목적지·일수·예산만
추출합니다. Weather·Place·Lodging·Budget Task의 필수값 중 인원·이동수단·제약이 없으므로
질문하고 어느 Agent도 호출하지 않습니다. 이어서 “1명, 대중교통, 제약 없음”이라고 답하면
앞서 모은 값과 합쳐 네 Agent를 실행합니다. 입력을 새로 시작하려면 화면의 입력 초기화를
누릅니다.

문장 해석은 교육용 규칙 기반이며 인식하지 못한 값을 추측하지 않습니다.
각 Agent의 실제 LLM 결과는 역할별 Pydantic 계약으로 검증합니다.

Weather는 Open-Meteo 날씨 Tool을 사용합니다. 강수량이나 3일 예보의 최대 강수 확률이
40% 이상이면 Place에 DB의 `indoor=true` 장소 조건을 전달합니다. Place 결과가 DB 후보이고 조건에
맞는지 확인한 뒤 숙소 Agent가 PostgreSQL의 교육용 1박 비용 기준으로 잠정 숙소 유형을
정합니다. Budget은 같은 비용 기준으로 전체 예산을 계산하며 앞서 정한 숙박 총액과
일치해야 합니다. 각 단계가 실패하면 뒤 Task는 실행하지 않고 Skip으로 표시합니다.
숙소 유형은 실제 호텔 예약·가격·가용성 확인 결과가 아닙니다.

DB에 `indoor` 필드를 추가했으므로 기존 DB는 `python -m mcp_server.database.init_db`를
다시 실행해 Seed를 갱신한 뒤 MCP와 Backend를 재시작합니다.

## 실제 Data Source

| Tool | Source | 설명 |
| --- | --- | --- |
| `get_weather` | `open-meteo` | 도시 좌표·현재 날씨·3일 예보 |
| `search_places` | `postgresql` | 장소·실내 여부·교통 메모·출처 URL·검증일 |
| `get_lodging_reference` | `postgresql` | 교육용 숙소 유형·1박 비용·숙박 총액 |
| `get_budget_reference` | `postgresql` | 교육용 보수적 비용 기준·출처·검증일 |

비용 기준은 실제 예약 가격이나 실시간 요금이 아닙니다. 계약·결정적 계산 실습을 위한
검증 가능한 교육용 기준이며 Tool Result의 `source_note`에 한계를 명시합니다.

다음 설정만 지원합니다.

```dotenv
WEATHER_DATA_SOURCE=live
TRAVEL_DATA_SOURCE=postgresql
```

다른 값을 사용하면 MCP Server 시작 단계에서 오류가 발생합니다.

## Redis 진행 상태와 Trace

Lab 07·08은 요청 직후 Run ID를 반환하고 Background에서 실행됩니다.

```http
POST /api/async-runs/multi-llm
POST /api/async-runs/verified-flow
GET  /api/async-runs/{run_id}/snapshot
```

Redis 저장 Key:

```text
mini02:run:{run_id}         # Hash: 현재 상태·진행률·최종 결과
mini02:run:{run_id}:events  # Stream: 시간순 Trace Event
```

Streamlit은 Snapshot API를 1초마다 조회하여 현재 Agent, 단계, 진행률, Trace를 표시합니다.
기본 TTL은 3,600초이며 `.env`의 `RUN_TTL_SECONDS`로 변경할 수 있습니다.

## 1. 환경 준비

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_02_role_task_contract
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` 설정:

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
WEATHER_DATA_SOURCE=live
TRAVEL_DATA_SOURCE=postgresql
DATABASE_URL=postgresql://agent_user:agent_pwd@127.0.0.1:5433/agent_db
REDIS_URL=redis://127.0.0.1:6379/0
RUN_TTL_SECONDS=3600
API_BASE_URL=http://127.0.0.1:8000
```

## 2. 공용 인프라와 DB Seed

```powershell
docker ps --filter "name=aidevs-pgvector"
docker ps --filter "name=aidevs-redis"
docker ps --filter "name=aidevs-ollama"
python -m mcp_server.database.init_db
```

직접 실행도 지원합니다.

```powershell
python .\mcp_server\database\init_db.py
```

02 전용 Schema에는 `places`, `budget_reference` Table만 생성합니다.

## 3. 세 Process 실행

01~05 프로젝트는 `8000`, `8010`, `8501`을 공유하므로 한 번에 하나만 실행합니다.

터미널 1:

```powershell
python .\mcp_server\main.py
```

터미널 2:

```powershell
uvicorn app.main:app --reload --port 8000 --app-dir backend
```

터미널 3:

```powershell
streamlit run .\frontend\app.py --server.port 8501
```

- 화면: `http://127.0.0.1:8501`
- API 문서: `http://127.0.0.1:8000/docs`
- MCP: `http://127.0.0.1:8010/mcp`

## 4. 환경 진단

```powershell
python .\check_environment.py
```

Cloud Key, Open-Meteo 설정, PostgreSQL Seed·출처, Redis, Ollama, Backend와 MCP Tool 4개를
검사합니다. Provider Key가 잘못된 경우 Tool 호출이 성공했더라도 LLM 단계는 실패로
기록됩니다. 하나라도 실패하면 진단 명령은 종료 코드 `1`을 반환합니다.

코드 변경 후 외부 서비스 없이 실행 가능한 회귀 테스트는 다음과 같이 확인합니다.

```powershell
python -m unittest discover -s tests -v
```

Gemini가 `429 RESOURCE_EXHAUSTED`를 반환하면 Agent 결과에
`error_code=quota_exhausted`, `retryable=true`, `retry_after_seconds`가 기록됩니다. 긴 Provider
원문 대신 짧은 재시도 안내를 표시하며, 다른 Provider로 자동 대체하지 않습니다.

## 주요 API

| Method | Path |
| --- | --- |
| GET | `/api/labs` |
| GET | `/api/role-cards` |
| GET | `/api/tasks` |
| POST | `/api/tasks/execute` |
| POST | `/api/tasks/execute-from-message` |
| POST | `/api/tasks/execute-multi-from-message` |
| GET | `/api/contracts` |
| GET | `/api/validation-cases` |
| POST | `/api/contracts/validate` |
| GET | `/api/incomplete-states` |
| GET | `/api/providers` |
| GET | `/api/agents` |
| GET | `/api/data-sources` |
| GET | `/api/mcp-status` |
| POST | `/api/async-runs/{flow_name}` |
| GET | `/api/async-runs/{run_id}/snapshot` |
| POST | `/api/runs/support-flow` |

동기 실행 API인 `/api/runs/multi-llm`, `/api/runs/verified-flow`도 제공하지만 화면에서는
실시간 진행 표시를 위해 비동기 API를 사용합니다.

## 포함하지 않는 범위

- 실제 예약·결제 실행
- 실시간 숙박·음식 가격
- 실제 고객 개인정보
- Redis TTL 이후의 영구 Trace 보관

영구 감사 이력이 필요하면 완료된 Redis Run과 Event를 PostgreSQL 이력 Table로 옮기는
구조를 추가해야 합니다.
