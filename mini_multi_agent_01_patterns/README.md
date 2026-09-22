# Mini Multi-Agent 01 · Orchestration Pattern Explorer

실제 LLM과 실제 Data Source를 이용해 Single Agent부터 Provider Failover까지 비교하는
교육용 프로젝트입니다. Mock 응답과 JSON fallback은 사용하지 않습니다.

## 핵심 원칙

- 날씨는 Open-Meteo Geocoding·Forecast API에서 실시간 조회합니다.
- 여행 지식, 고객지원, 콘텐츠 사실, 품질 기준은 PostgreSQL에서 조회합니다.
- 예산은 사용자 입력값으로 결정적으로 계산합니다.
- Agent는 허용된 MCP Tool 결과만 사실 근거로 사용합니다.
- 외부 API나 DB가 실패하면 가상 데이터로 대체하지 않고 실행을 실패 처리합니다.
- Provider Failover는 Lab 13에서 명시적으로 선택했을 때만 수행합니다.

PostgreSQL 데이터는 실제 SQL Query 흐름을 위한 검증 가능한 교육용 Seed입니다. 실제 고객
개인정보나 예약·결제 데이터는 포함하지 않습니다. 지식 Row에는 가능한 경우
`source_url`과 `verified_at`을 저장합니다.

## 전체 구조

```text
Streamlit :8501
  → FastAPI :8000
    → PatternEngine
      ├─ GPT / Gemini / Llama / Gemma
      └─ HTTP MCP Client
        → FastMCP :8010
          ├─ Open-Meteo API
          ├─ PostgreSQL :5433
          └─ 결정적 예산 계산
```

## 데이터 출처

| 영역 | Source | 비고 |
| --- | --- | --- |
| 날씨 | `open-meteo` | 현재 날씨와 3일 예보 |
| 장소·교통·알레르기 | `postgresql` | 출처 URL과 검증일 포함 |
| 주문·환불·도움말 | `postgresql` | 01 전용 교육용 업무 데이터 |
| 콘텐츠 사실 | `postgresql` | 출처가 있는 부산 사실 |
| 콘텐츠·코드 완료 조건 | `postgresql` | 평가와 검토 기준 |
| 여행 예산 | `deterministic-calculation` | 기간·인원·총예산에서 계산 |

Mock/JSON 모드는 제거되었습니다. 다음 값 이외의 설정으로 MCP Server를 시작하면 오류가
발생합니다.

```dotenv
WEATHER_DATA_SOURCE=live
SUPPORT_DATA_SOURCE=postgresql
```

## Lab 01~13

| Lab | Pattern | 실제 데이터 사용 |
| --- | --- | --- |
| 01 | Single Agent | 날씨·장소·교통·알레르기·예산 |
| 02 | Independent Agents | 각 전문 Agent의 여행 Tool 결과 |
| 03 | Agent 분리 판단 | 사용자가 선택한 분리 조건 |
| 04 | 아키텍처 비용 비교 | 선택한 Agent 수의 결정적 계산 |
| 05 | Context와 Tool 권한 | Backend Agent Registry의 실제 권한 |
| 06 | Orchestration 비교 | 실제 날씨·예산 결과 비교 |
| 07 | Sequential | PostgreSQL 사실·검수 기준 |
| 08 | Parallel + Join | 여행 Tool 병렬 조회와 Join |
| 09 | Router | PostgreSQL 주문·환불·기술지원 |
| 10 | Supervisor–Worker | PostgreSQL 코드 완료 조건 |
| 11 | Handoff | PostgreSQL 주문 상태·환불 정책 |
| 12 | Evaluator–Reviser | PostgreSQL 사실·평가 기준 |
| 13 | Provider Failover | PostgreSQL 사실 + 실제 Secondary Provider |

각 Lab에는 사용자 요청 예시가 3개씩 있습니다. 예시를 선택하면 요청 입력창에 반영되며,
그대로 실행하거나 수정할 수 있습니다.

## 프로젝트 구조

```text
backend/app/
├─ agents/                  # Agent 역할·지시문·Tool 권한
├─ orchestration/engine.py  # Pattern 실행·분기·반복·종료
├─ providers/registry.py    # 네 LLM Provider Adapter
├─ mcp/client.py            # HTTP MCP Client
├─ routers/patterns.py      # FastAPI Endpoint
└─ schemas/runs.py          # 요청·응답 계약

mcp_server/
├─ main.py                  # 11개 MCP Tool 등록
├─ tools/                   # 여행·지원·콘텐츠 Tool
├─ database/
│  ├─ connection.py        # 읽기 전용 Query 연결
│  ├─ support_queries.py
│  ├─ knowledge_queries.py
│  ├─ schema.sql           # Schema와 Seed
│  └─ init_db.py
└─ weather/client.py        # Open-Meteo Client

frontend/app.py             # Streamlit UI와 39개 요청 예시
check_environment.py        # 실행 환경 진단
```

## 1. 환경 준비

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_01_patterns
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.venv`는 복사하지 말고 현재 설치된 Python으로 생성합니다. `.env`에서 Cloud API Key와
Model을 설정합니다.

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
GEMMA_MODEL=gemma3:4b
MCP_HOST=127.0.0.1
MCP_PORT=8010
MCP_URL=http://127.0.0.1:8010/mcp
WEATHER_DATA_SOURCE=live
SUPPORT_DATA_SOURCE=postgresql
DATABASE_URL=postgresql://agent_user:agent_pwd@127.0.0.1:5433/agent_db
API_BASE_URL=http://127.0.0.1:8000
```

## 2. PostgreSQL 초기화

```powershell
docker ps --filter "name=aidevs-pgvector"
python -m mcp_server.database.init_db
```

직접 실행도 지원합니다.

```powershell
python .\mcp_server\database\init_db.py
```

생성 Table:

```text
orders, refund_policies, help_articles
travel_places, transit_guides, allergy_guidance
content_facts, quality_requirements
```

## 3. Ollama 준비

```powershell
docker ps --filter "name=aidevs-ollama"
docker exec aidevs-ollama ollama list
```

Model이 없을 때만 설치합니다.

```powershell
docker exec aidevs-ollama ollama pull llama3.2
docker exec aidevs-ollama ollama pull gemma3:4b
```

## 4. 세 Process 실행

01~05 프로젝트는 Backend `8000`, MCP `8010`을 공통 사용하므로 한 번에 하나만 실행합니다.

터미널 1 · MCP Server:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_01_patterns
.\.venv\Scripts\Activate.ps1
python .\mcp_server\main.py
```

터미널 2 · FastAPI Backend:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_01_patterns
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000 --app-dir backend
```

터미널 3 · Streamlit Frontend:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_01_patterns
.\.venv\Scripts\Activate.ps1
streamlit run .\frontend\app.py --server.port 8501
```

- 화면: `http://127.0.0.1:8501`
- API 문서: `http://127.0.0.1:8000/docs`
- MCP: `http://127.0.0.1:8010/mcp`

## 5. 환경 진단

세 Process를 실행한 뒤 확인합니다.

```powershell
python .\check_environment.py
```

Provider, Data Source, PostgreSQL 8개 Table, Ollama Model, Backend·MCP 연결, Tool 11개를
검사합니다. 실패를 Mock 성공으로 바꾸지 않습니다.

## Trace 확인

`실행 Trace > details > tool_results`에서 Tool 이름, `source`, `source_url`,
`verified_at`, Provider, Model, 지연시간과 오류를 확인합니다.

## 포함하지 않는 범위

- 실제 예약·환불·결제 변경
- 실제 고객 개인정보
- 실시간 교통 도착 시각과 실시간 요금
- Human Approval, Redis Queue, 장기 실행 Worker

조회되지 않은 정보는 LLM이 사실처럼 보완하지 않고 추가 확인 필요로 표시해야 합니다.
