# Mini Multi-Agent 04 · Distributed Collaboration

여러 Agent의 실행 순서를 계획하고, 독립 작업을 동시에 실행한 뒤 결과를 하나로 합치는
방법을 학습합니다. 01에서 본 Pattern을 02의 계약과 03의 선택 구조 위에서 다시 실행합니다.

## 01~03에서 04로 이어지는 내용

04는 새로운 Pattern을 많이 추가하는 과정이 아닙니다. 앞에서 실행했던 Sequential과
Parallel을 Shared State에 기록하고, 필요한 결과가 준비되었을 때 Join하는 방법을 배웁니다.

```text
01: 여러 Orchestration Pattern 실행
02: Agent Role·Task·Contract 정의
03: 요청과 상태를 보고 실행할 Agent 선택
04: 여러 Agent를 계획대로 실행하고 결과 합치기
```

04에서 꼭 기억할 문장은 세 개입니다.

```text
Execution Plan은 Agent 실행 순서를 정합니다.
Shared State는 완료 결과와 실패를 기록합니다.
Join은 필요한 결과가 준비된 뒤에 실행합니다.
```

| 코드 용어 | 쉬운 의미 |
| --- | --- |
| Execution Plan | Agent 실행 순서표 |
| Sequential | 앞 결과를 다음 Agent에게 전달하며 순서대로 실행 |
| Parallel | 서로 독립적인 Agent를 동시에 실행 |
| Shared State | 지금까지 완료된 결과와 실패 기록 |
| Join | 여러 결과를 모아 최종 결과 생성 |
| Partial Failure | 일부 Agent만 실패한 상태 |

## 실행 구조

```text
Streamlit :8540 ──SSE──→ FastAPI :8000 → MCP :8010
      └──Snapshot API──→      ├→ GPT·Gemini·Llama·Gemma
                             └→ Redis Hash + Stream
```

왼쪽 메뉴에는 01 Execution Plan부터 10 날씨에 따른 장소와 예산, Agent Registry,
Shared State, Trace Explorer, MCP Tool과 Provider 상태가 있습니다.

## 프로젝트 구조

```text
backend/app/
├─ agents/
│  ├─ coordinator_agent.py       # 핵심 실행 조정: Python
│  ├─ aggregator_agent.py        # 핵심 결과 통합: Python
│  ├─ definitions/workers.yaml   # 반복 Worker 선언
│  ├─ definitions/teams.yaml     # 병렬 Team 구성
│  ├─ loader.py
│  └─ registry.py
├─ orchestration/engine.py       # 병렬 실행·Join·실패·종료 정책
├─ orchestration/event_flow.py   # 같은 구조를 온라인 행사에 적용
├─ orchestration/langgraph_flow.py # 여행 순차 Context 전달을 LangGraph로 구성
├─ mcp/client.py                 # Tool 권한 확인과 MCP 호출
├─ observability/tracker.py      # 실행 상태와 Event 발행
├─ storage/redis_store.py        # Redis Hash + Stream
├─ routers/collaboration.py      # REST + SSE Endpoint
├─ providers/ · schemas/
frontend/app.py                  # 왼쪽 메뉴·SSE·Snapshot 복구
mcp_server/
├─ main.py                       # MCP Server 생성과 Tool 등록
├─ core/config.py                # MCP·PostgreSQL 환경 설정
├─ database/
│  ├─ connection.py             # 읽기 전용 연결
│  ├─ collaboration_queries.py  # 장소·예산·주문·정책 Query
│  ├─ schema.sql                # mini_multi_agent_04 Schema와 Seed
│  └─ init_db.py
└─ tools/
   ├─ weather_tools.py           # 실제 Open-Meteo
   ├─ travel_tools.py            # PostgreSQL 장소·예산
   └─ support_tools.py           # PostgreSQL 주문·환불 정책
```

## Python + YAML 운영형 Registry

| Python에 유지 | YAML로 관리 |
| --- | --- |
| Coordinator·Aggregator 핵심 역할 | 반복 Worker의 이름·목표·지시문 |
| `asyncio` 병렬 실행 | Worker별 Provider와 출력 계약 |
| Timeout·실패·Join·종료 정책 | Worker별 허용 MCP Tool |
| Tool 권한 최종 검증 | Team의 Worker 구성 |

YAML은 실행 코드가 아닙니다. Team 구성을 읽더라도 필수 결과 확인, 부분 실패 정책과
최종 종료 판단은 Python Orchestrator가 담당합니다.

## 심화 · SSE와 Snapshot

기본 수업에서는 Agent 완료 순서와 Join 결과만 확인합니다. 내부적으로는 02에서 사용한
Polling을 발전시켜 SSE로 Event를 즉시 전달합니다.

```text
POST /api/stream-runs/distributed       → run_id 반환
GET  /api/stream-runs/{run_id}/events   → SSE 실시간 Event
GET  /api/stream-runs/{run_id}/snapshot → 새로고침·재연결 상태 복구
```

- Redis Hash: 실행의 최신 상태와 진행률
- Redis Stream: Agent 시작·완료·실패·Join Event
- SSE: Redis Event를 브라우저에 단방향 전송
- Snapshot API: SSE 연결이 끊겼을 때 현재 상태 복구

## 환경 준비

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_04_distributed_collaboration
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 OpenAI와 Gemini API Key를 설정합니다. Llama와 Gemma는 공용
`aidevs-ollama`의 `http://127.0.0.1:11434`를 사용합니다.
Gemma 기본 모델은 `gemma3:1b`입니다.
Redis는 기존 `aidevs-redis`의 `redis://127.0.0.1:6379/0`을 사용합니다.
장소·예산·주문·환불 정책은 기존 PostgreSQL의 `mini_multi_agent_04` Schema를 사용합니다.
Redis의 최신 상태와 실행 Event는 `RUN_TTL_SECONDS`(기본 3600초) 후 만료됩니다.

이번 데이터는 도시·주문번호·정책 Key로 정확히 조회하는 구조화 데이터이므로 SQL이
RAG보다 적합합니다. 향후 긴 약관 문서 여러 개에서 의미가 비슷한 내용을 찾아야 할 때
`pgvector + Embedding` 기반 RAG를 추가합니다. 단순한 정확 조회를 RAG로 바꾸지는 않습니다.

최초 한 번 Schema와 Seed 데이터를 준비합니다.

```powershell
python .\mcp_server\database\init_db.py
```

## 세 Process 실행

미니 프로젝트 01~05는 Backend `8000`, MCP `8010`을 공통 사용하므로 한 번에 하나의
프로젝트만 실행합니다.

터미널 1:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_04_distributed_collaboration\mcp_server
..\.venv\Scripts\Activate.ps1
python main.py
```

터미널 2:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_04_distributed_collaboration
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000 --app-dir backend
```

터미널 3:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_04_distributed_collaboration
.\.venv\Scripts\Activate.ps1
streamlit run .\frontend\app.py --server.port 8540
```

- 화면: `http://127.0.0.1:8540`
- API 문서: `http://127.0.0.1:8000/docs`
- MCP: `http://127.0.0.1:8010/mcp`

## Lab과 호출 수

| Lab | 내용 | 예상 LLM 호출 |
| --- | --- | ---: |
| 01 | Execution Plan 검증 | 0회 |
| 02 | Gemini→GPT→Gemma Sequential | 최대 3회 |
| 03 | Gemini·Llama·GPT Parallel | 3회 |
| 04 | Parallel + Gemma Join | 최대 4회 |
| 05 | Partial Failure 정책 | 3회 |
| 06 | Support 질문 분류 → Refund·Delivery Handoff 또는 직접 답변 | 1~2회 |
| 07 | 네 LLM Distributed Workflow | 최대 4회 |
| 08 | 온라인 행사 Parallel + Join | 최대 4회 |
| 11 | 모의 온라인 주문: 재고·결제 필수, 쿠폰 선택 Join Guard | 2~4회 |

## 초보자용 진행 순서

| Lab | 먼저 확인할 내용 | 먼저 읽을 코드 |
| --- | --- | --- |
| 01 | 어떤 Agent를 먼저 실행하는가 | `contracts.py`의 `ExecutionPlan` |
| 02 | 앞 결과를 다음 Agent에게 전달 | `engine.py`의 `sequential()` |
| 03 | 세 Agent를 동시에 실행 | `engine.py`의 `parallel()` |
| 04 | 필수 결과 확인 후 일정 생성 | `engine.py`의 `join()` |
| 05 | 필수 Agent와 선택 Agent 실패 비교 | `engine.py`의 `partial_policy()` |
| 06 | Support가 환불·배송 중 선택하거나 직접 답변 | `engine.py`의 `handoff()` |
| 07 | 병렬 실행과 Join을 한 번에 실행 | `engine.py`의 `distributed_tracked()` |
| 08 | 같은 구조를 다른 업무에 적용 | `event_flow.py`의 `event_collaboration()` |
| 11 | 필수 결과가 모인 뒤 주문 안내 | `order_flow.py`의 `order_collaboration()` |

화면을 먼저 실행하고 표에 적힌 Class나 함수 하나만 읽습니다. Redis Stream, SSE,
Snapshot 복구는 기본 흐름을 이해한 뒤 살펴보는 심화 내용입니다.

07에서는 세 병렬 Worker가 완료되는 실제 순서대로 SSE Event가 화면에 표시되고,
필수 Worker 결과가 준비되면 Gemma Aggregator가 Join을 수행합니다.

## Lab 08 · 다른 업무에 Parallel + Join 적용

여행 예제에서 배운 실행 구조를 온라인 행사 준비에 그대로 적용합니다. 새로운 Pattern을
추가하는 것이 아니라, **업무가 달라져도 Parallel과 Join의 원리는 같다**는 점을
확인하는 예제입니다.

```text
온라인 행사 요청
├─ Gemini event_content_agent  ─┐
├─ Llama event_promotion_agent ─┼─ 동시에 실행
└─ OpenAI event_operation_agent ┘
                   ↓ 필수 결과 확인
Gemma 3 1B event_plan_agent가 하나의 행사안으로 Join
```

콘텐츠와 운영 결과는 필수이고 홍보 결과는 선택입니다. 필수 결과가 없으면 최종 Agent를
실행하지 않습니다. 데이터베이스와 MCP Tool은 추가하지 않았으므로 학생은 다음 두 곳만
읽으면 됩니다.

- `backend/app/agents/definitions/teams.yaml`의 `event_collaboration_team`
- `backend/app/orchestration/event_flow.py`의 `event_collaboration()`

기존 여행 Team과 새 행사 Team의 `parallel_workers`, `required_workers`, `aggregator`를
나란히 비교하면 재사용되는 구조를 쉽게 확인할 수 있습니다.

날씨 Tool은 Open-Meteo의 실제 서울·부산·제주 예보를 조회합니다. 장소·도시별 일일
예산·주문 상태·환불 정책은 PostgreSQL에서 조회하고 예산 합계만 Python이 결정적으로
계산합니다. Agent의 해석과 결과 생성은 실제 LLM이 수행하며 Provider·MCP·DB·계약
오류를 고정 성공 결과로 대체하지 않습니다.

## Python이 보장하는 경계

- Worker는 Shared State를 직접 수정하지 않습니다.
- Orchestrator만 결과와 Trace를 기록합니다.
- Join은 필수 결과가 모두 있을 때만 실행합니다.
- 부분 실패 정책은 미리 선택합니다.
- Handoff는 05 과정에서 자세히 배우며, 04에서는 질문에 따라 환불·배송 인계 또는 직접 답변으로 분기하는 흐름을 확인합니다.
- 실패 결과는 완료 Agent 목록에 추가하지 않습니다.
- SSE가 끊겨도 Snapshot API에서 동일한 `run_id` 상태를 복구합니다.
- Worker 선언을 YAML로 관리해도 실행 정책은 Python이 최종 통제합니다.

## 주요 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| GET | `/api/registry` | Python·YAML Agent 및 Team Registry |
| POST | `/api/stream-runs/distributed` | SSE용 분산 실행 생성 |
| GET | `/api/stream-runs/{run_id}/events` | Redis Stream 기반 SSE |
| GET | `/api/stream-runs/{run_id}/snapshot` | 최신 진행 상태 복구 |
| GET | `/api/mcp-status` | MCP Tool 연결 상태 |
| POST | `/api/runs/event-collaboration` | 온라인 행사 Parallel + Join 실행 |

## 검증

환경 진단은 하나라도 실패하면 종료 코드 `1`을 반환합니다. 외부 서비스 없이 실행 가능한
회귀 테스트도 함께 제공합니다.

```powershell
python -m unittest discover -s tests -v
python .\check_environment.py
```

Gemini `429 RESOURCE_EXHAUSTED`는 `quota_exhausted`와 재시도 가능 시간으로 정규화하며,
다른 Provider로 자동 대체하지 않습니다.

## 09 · LangGraph 여행 Workflow

Weather → Place → Lodging → Budget → Guide Agent를 순서대로 실행합니다. 각 Agent는
앞 단계까지의 검증된 결과를 누적 Context로 전달받습니다. 어느 단계든 실패하면 조건
Edge가 즉시 END로 이동하므로 뒤 Agent는 근거 없는 결과를 만들지 않습니다. 07의 병렬
실행·Join 흐름과 비교해, 09에서는 결과 의존성이 있는 작업을 LangGraph의 Node·Edge·State로
표현합니다. Provider 호출과 Tool, 출력 계약은 기존 코드를 재사용합니다.

```text
POST /api/runs/langgraph  JSON: {"message": "부산 2박 3일, 1명, 대중교통 여행을 계획해 주세요."}
START → Weather → Place → Lodging → Budget → Guide → END
```

09는 요청이 완료되면 전체 trace를 반환합니다. 07의 SSE·Redis 실시간 표시와 구분해
Graph 실행 경로를 먼저 살펴보세요. 실행 전 `pip install -r requirements.txt`로
LangGraph 의존성을 설치해야 합니다.

## 10 · 날씨에 따른 장소와 예산

09의 선형 순차 실행과 달리, 10은 앞 단계의 결과가 다음 Node를 결정하는 조건 분기까지 다룹니다.
Weather Agent의 Open-Meteo 강수확률이 설정한 기준 이상이면 실내, 아니면 실외
장소 경로로 이동합니다. Place Agent가 PostgreSQL에서 조회한 후보 중 해당 경로의
장소를 선택하고, Budget Agent의 도시별 기준 금액에 장소의 1인 예상 비용 × 인원을
더해 사용자 예산과 비교합니다. 선택 규칙은 Python Guard에 있으며 LLM의 문장만으로
분기하거나 비용을 계산하지 않습니다.

```text
POST /api/runs/weather-place-budget
JSON: {"message": "부산 2박 3일, 1명, 대중교통 여행", "budget_limit": 650000, "rain_threshold": 50}
날씨 → 강수확률 Guard → 실내/실외 장소 → 예산
```

강수확률은 조회 시점부터 최대 3일 예보의 최대값입니다. 여행 날짜 지정 기능은
포함하지 않았습니다. 실내·실외와 예상 비용 필드는 장소 DB에 추가되므로 기존
설치에서는 기존 주문·정책 데이터를 유지하는 `python .\mcp_server\database\migrate_lab10.py`를 실행해 주세요. 새 설치는 `init_db.py`가 10번 데이터를 함께 준비합니다.

10번 화면에서 Open-Meteo 조회가 시간 초과될 경우 오류를 그대로 표시합니다.
학습용으로 실내·실외 분기만 확인하려면 `교육용 강수확률 직접 입력`을 선택하세요.
이 값은 `weather_source=user_input`으로 표시되며 실제 날씨로 취급하지 않습니다.

## Lab 11 · 온라인 주문 Join Guard

재고 확인과 결제 확인은 필수 결과이고 쿠폰 안내는 선택 결과입니다. 세 모의 Agent를 병렬 실행하고,
Python Join Guard가 필수 결과 둘을 확인한 뒤에만 주문 안내 Agent를 호출합니다.
화면에서 재고·결제·쿠폰 중 하나의 교육용 실패를 선택해 차단과 계속 진행을 비교할 수 있습니다.
이 예제는 실제 재고·결제·주문 확정을 실행하지 않습니다.
