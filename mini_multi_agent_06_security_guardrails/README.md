# Mini Multi-Agent 06 · AI Security and Guardrails

01~05에서 만든 역할·계약·Supervisor·분산 실행·Handoff 구조에 여러 겹의 보안 경계를 추가합니다. 01~07은 입력 후 버튼을 눌러 가상 Agent/LLM 결과와 실제 Python Guard 판단을 확인합니다. 외부 LLM, DB, Redis, API Key는 필요하지 않습니다. 08 이후의 통합 예제에서는 실제 OpenAI와 Gemma, Open-Meteo MCP를 사용하지만 보안 판단은 계속 Python이 수행합니다.

```text
사용자 요청
→ Input Guard Agent
→ Context Guard
→ Tool Permission Guard
→ Open-Meteo MCP
→ OpenAI Travel Agent
→ Approval Boundary
→ Gemma Response Agent
→ Response Guard Agent
→ Redis Audit Event → 폴링 화면
```

## 이번 프로젝트의 핵심 원칙

- 실제 LLM 실패를 Mock 성공으로 바꾸지 않습니다.
- Prompt Injection 필터 하나를 완벽한 방어로 설명하지 않습니다.
- 역할 설명은 권한이 아닙니다. Tool 실행 직전에 Python allowlist를 검사합니다.
- 모든 Agent에 전체 State를 주지 않고 YAML에 선언한 최소 Context만 전달합니다.
- 변경 Tool은 사용자 승인 없이 실행하지 않습니다.
- 최종 응답은 사용자에게 보내기 전에 별도 Policy로 검사합니다.
- 허용뿐 아니라 차단과 실패도 Redis Audit Event로 남깁니다.

## 학습 메뉴

| 메뉴 | 학습 내용 | 실행 방식 |
| --- | --- | --- |
| 01 Prompt Injection | 요청 입력 후 정상·공격 사례 검사 | 가상 답변 + Python Guard |
| 02 Input Validation | 여행지·일수·인원 입력 후 범위 검사 | Pydantic + 가상 답변 |
| 03 Response Policy | 가상 LLM 답변 입력 후 전달 여부 검사 | Python Guard |
| 04 Agent·Tool Permission | Agent와 Tool 선택 후 권한 검사 | YAML + Python Guard |
| 05 Approval Boundary | 작업·사용자와 승인 일치 여부 검사 | 가상 저장 + Python Guard |
| 06 Idempotent Write | 같은 키로 저장 버튼을 실제 두 번 눌러 첫 저장과 결과 재사용 비교 | 수업용 메모리 기반 중복 방지 |
| 07 Context Access | Agent별 Context와 사용자 범위 확인 | YAML + Python Guard |
| 08 Integrated Guardrail | 실제 LLM·MCP·Redis 통합 | OpenAI + Gemma + Open-Meteo |
| 09 다른 업무에 Guardrail 적용 | 고객지원 입력·Context·응답 검사 | OpenAI + Gemma, DB·MCP 없음 |
| 10 Human-in-the-loop Approval | 초안 확인 후 승인·거부와 실행 재개 | 별도 승인 API + Redis 저장 |
| 11 Enterprise Data Leak Guard | 회사 기밀·개인정보 외부 전송 방지 | Python Guard + 마스킹/차단 |
| 12 Policy Database Guard | 보안 정책을 DB처럼 읽어 적용 | 정책 저장소 + block/mask |
| 13 Double Click Idempotency | 저장 버튼 두 번 클릭 중복 방지 | Redis 멱등성 키 |

01~13 화면에는 각 실습의 입력·검사·허용/차단 분기를 보여 주는 흐름도가 있습니다. 01~07은 직접 바꿀 수 있는 입력값과 가상 LLM·Tool 결과를 사용하며 외부 호출은 없습니다. 08~13은 화면의 흐름도와 실행 추적을 비교합니다. 12의 정책 목록은 실제 DB가 아닌 Python 리스트입니다.

## 디렉터리 구조

```text
backend/app/
├─ agents/
│  ├─ definitions/security_policies.yaml
│  ├─ input_guard_agent.py
│  ├─ response_guard_agent.py
│  ├─ tool_guard_agent.py
│  ├─ travel_agent.py
│  └─ registry.py
├─ orchestration/engine.py
├─ orchestration/support_flow.py # 고객지원 Guardrail 적용 예제
├─ schemas/contracts.py
├─ mcp/client.py
├─ providers/registry.py
├─ observability/tracker.py
├─ storage/redis_store.py
└─ routers/security.py
frontend/app.py
mcp_server/
├─ main.py
├─ core/config.py
└─ tools/weather_tools.py
```

## Agent와 Policy 관리 기준

Agent의 이름·목표·설명·지시문처럼 수업에서 읽어야 하는 정의는 `registry.py`의 `AgentProfile`로 명확하게 작성했습니다. 반복되고 운영 중 변경할 수 있는 차단 문구, Tool 목록, Context 필드는 `security_policies.yaml`에서 관리합니다.

| Python이 강제하는 것 | YAML이 선언하는 것 |
| --- | --- |
| Pydantic 입력 계약 | 입력 차단 문구와 최대 길이 |
| Tool 실행 전 권한 확인 | Agent별 허용 Tool |
| 승인 여부 확인 | 변경 Tool 목록 |
| Workflow 중단과 상태 변경 | Agent별 Context 필드 |
| 응답 차단과 Audit 기록 | 응답 차단 문구 |

## 실제 연결

- OpenAI: 검증된 Context로 여행 초안 생성
- Gemma: 로컬 Ollama 컨테이너에서 사용자용 최종 답변 생성
- Open-Meteo: MCP Server의 `get_weather` Tool이 실제 날씨 조회
- Redis: 실행 Snapshot과 Audit Event 저장
- Frontend: SSE가 아닌 1초 주기 폴링으로 Progress Bar와 현재 상태 갱신

별도 Docker Compose를 만들지 않습니다. 기존 `aidevs-ollama`, `aidevs-redis` 컨테이너를 사용합니다.
Snapshot, Audit Event와 멱등성 Claim은 `RUN_TTL_SECONDS`(기본 3600초) 후 만료됩니다.

## 환경 준비

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_06_security_guardrails
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 `OPENAI_API_KEY`를 입력합니다. 기본 모델은 `gpt-4.1-mini`, 로컬 모델은 `gemma3:1b`입니다.

```powershell
python .\check_environment.py
```

## 세 Process 실행

01~06 미니 프로젝트는 Backend `8000`, MCP `8010`을 공통 사용하므로 한 번에 하나만 실행합니다.

터미널 1 · MCP Server:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_06_security_guardrails\mcp_server
..\.venv\Scripts\Activate.ps1
python main.py
```

터미널 2 · Backend:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_06_security_guardrails
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000 --app-dir backend
```

터미널 3 · Frontend:

```powershell
cd C:\mini_multi_agent_st\mini_multi_agent_06_security_guardrails
.\.venv\Scripts\Activate.ps1
streamlit run .\frontend\app.py --server.port 8560
```

- 화면: `http://127.0.0.1:8560`
- API 문서: `http://127.0.0.1:8000/docs`
- MCP: `http://127.0.0.1:8010/mcp`

## 주요 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| GET | `/api/labs` | 13개 학습 메뉴 |
| GET | `/api/registry` | Python Agent와 YAML Policy |
| GET | `/api/demo-cases` | 정상·차단 비교 사례 |
| GET | `/api/security-seed-examples` | Lab 11~13 화면에서 사용하는 시드 데이터 |
| GET | `/api/providers` | 실제 LLM 설정·연결 상태 |
| GET | `/api/mcp-status` | 실제 MCP Tool 상태 |
| POST | `/api/runs` | Guardrail Workflow 생성 |
| GET | `/api/runs/{run_id}` | Snapshot과 Audit Event 폴링 |
| POST | `/api/runs/support-guardrail` | 고객지원 Guardrail 실행 |
| POST | `/api/approval-runs` | 승인 대기형 여행 Workflow 생성 |
| GET | `/api/approval-runs/{run_id}` | 승인할 초안·실행 인자·Audit Event 조회 |
| POST | `/api/approval-runs/{run_id}/decision` | `X-User-ID`와 실행별 `X-Approval-Token`을 확인한 승인 또는 거부 |
| POST | `/api/runs/enterprise-data-leak` | 직원 입력의 개인정보·회사 기밀을 외부 LLM 호출 전 검사 |
| POST | `/api/runs/policy-database-guard` | 정책 저장소에서 읽은 규칙으로 block/mask 판단 |
| POST | `/api/runs/double-click-idempotency` | 저장 버튼 두 번 클릭 상황에서 실제 저장 1회만 실행 |

## Lab 09 · 다른 업무에 Guardrail 적용

Lab 08의 여행 Workflow와 같은 보안 순서를 고객지원 답변에 적용합니다. 새로운 보안
Pattern을 추가하기보다 업무가 바뀌어도 입력·Context·응답 경계는 유지된다는 점을
확인합니다.

```text
고객 문의
→ Python 입력 검사
→ 고객 ID·문제 내용만 최소 Context로 선택
→ OpenAI support_draft_agent가 초안 작성
→ Gemma 3 1B support_answer_agent가 답변 정리
→ Python 응답 검사
```

`internal_note`와 `api_key`는 예제의 전체 Context에는 존재하지만 다음 Agent에게 전달되지
않습니다. Prompt Injection 예시는 첫 단계에서 차단되므로 OpenAI와 Gemma를 호출하지
않습니다. 이 예제에는 새 데이터베이스와 MCP Tool을 추가하지 않았습니다.

학생은 다음 두 파일을 먼저 읽습니다.

- `backend/app/orchestration/support_flow.py`의 `run_support_guardrail()`
- `backend/app/agents/definitions/security_policies.yaml`의 고객지원 Context 목록

여행 예제와 고객지원 예제를 비교하여 업무마다 달라지는 입력과 Agent, 그대로 유지되는
입력 검사→최소 Context→LLM→응답 검사 순서를 구분할 수 있습니다.

## Lab 10 · Human-in-the-loop Approval

Lab 05의 실행 전 Boolean 승인을 실제 일시 정지형 승인 흐름으로 확장합니다. 화면의
흐름도는 Input Guard → Weather Agent → 숙소 후보 → Travel Agent → 사용자 승인
→ 교육용 예약 저장 순서를 보여 줍니다. 비 오는 날과 비 오지 않는 날을 선택하면
숙소 후보의 추천 순서가 달라집니다. 실제 날씨는 MCP에서 별도로 조회하여 참고용으로
보여 줍니다. 조회가 실패해도 선택한 시나리오로 실습할 수 있습니다.

OpenAI가 여행 초안을 만들면 Workflow는 `pending_approval` 상태로 멈춥니다.
이때 숙소 후보와 일정 초안을 확인하고 숙소 하나를 선택한 뒤 승인하거나 거부합니다.

```text
입력 검사 → 실제 날씨 조회 → 비/맑음 시나리오별 숙소 후보 → 일정 초안 생성
→ pending_approval에서 일시 정지
→ 사용자 승인: 숙소 선택·소유자·승인 ID·만료·일정 인자 Hash 검사 → Redis 교육용 예약 → completed
→ 사용자 거부: 저장하지 않음 → rejected
```

승인은 최초 요청의 체크박스가 아니라 별도 결정 API로 제출합니다. 서버는
`X-User-ID`가 실행 소유자와 같은지 확인하고 생성 응답에서 한 번 전달한 실행별
`X-Approval-Token`도 함께 검증합니다. 승인 화면에 표시된 실행 인자의 Hash가
달라지지 않았는지도 검사합니다. Token 원문은 Snapshot에 저장하지 않습니다.
승인 요청은 10분 후 만료되며 멱등성 키가 같은 저장의 중복 실행을 차단합니다.
숙소 후보는 `demo_seed_data.py`의 부산 시드 3건입니다. `book_demo_hotel`
권한 검사를 통과한 경우에만 Redis에 교육용 예약 기록을 저장합니다.
실제 호텔 예약 시스템이나 결제는 호출하지 않습니다.



## Lab 11 · Enterprise Data Leak Guard

회사 내부 AI 서비스에서는 직원이 악의가 없어도 고객 이메일, 전화번호, API Key, 내부 프로젝트 코드명 같은 값을 붙여 넣을 수 있습니다. 이 Lab은 외부 LLM 호출 전에 Python Guard가 입력을 검사하고, 마스킹 가능한 값은 가리고 위험한 값은 차단하는 흐름을 보여 줍니다.

```text
직원 입력
→ 개인정보와 회사 기밀 패턴 검사
→ 이메일/전화번호는 마스킹
→ API Key, access_token, INTERNAL_ONLY는 차단
→ 허용된 문장만 LLM 경계로 전달
```

화면에는 직원이 입력한 원문과 Guard 처리 후 **LLM에 전달할 예정인 Context**를 나란히 표시합니다. 이메일·전화번호는 마스킹된 값만 Context에 들어가고, API Key·회사 기밀은 Context 자체가 생성되지 않습니다. 이 Lab은 실제 외부 LLM 호출을 하지 않습니다.

## Lab 12 · Policy Database Guard

보안 정책은 운영 중 자주 바뀔 수 있습니다. 이 Lab은 실제 DB 대신 Python list를 사용하지만, 구조는 정책 저장소에서 규칙을 읽어 `block`, `mask`, `allow`를 판단하는 방식입니다. 운영 환경에서는 Supabase, PostgreSQL, Redis, 사내 정책 DB로 바꿀 수 있습니다.

## Lab 13 · Double Click Idempotency

사용자가 저장 버튼을 실수로 두 번 클릭하거나 네트워크 재시도로 같은 요청이 다시 도착할 수 있습니다. 이 Lab은 같은 `idempotency_key`가 들어온 두 요청 중 첫 번째만 실제 저장하고, 두 번째는 이전 결과를 재사용하는 흐름을 보여 줍니다.

## 통합 실습 순서

1. Lab 08에서 정상 요청을 실행하고 입력·Context·Tool·LLM·응답 검사 순서를 확인합니다.
2. Prompt Injection 요청을 실행하고 입력 단계에서 `blocked`되는지 확인합니다.
3. MCP와 LLM이 차단된 요청에는 호출되지 않는지 확인합니다.
4. YAML의 차단 문구를 하나 추가하고 같은 요청을 다시 실행합니다.
5. Lab 10에서 초안을 만든 뒤 `pending_approval` 상태와 저장 인자를 확인합니다.
6. 거부 시 저장되지 않고, 승인 시 한 번만 Redis에 저장되는지 확인합니다.

## 완료 기준

- 입력 Guard와 응답 Guard의 차이를 설명할 수 있습니다.
- Agent Profile과 Tool 권한의 차이를 설명할 수 있습니다.
- 최소 Context, 승인, 멱등성이 서로 다른 문제임을 이해합니다.
- 실제 OpenAI·Gemma·Open-Meteo 실행의 Audit Event를 화면에서 확인합니다.
- Prompt Injection 요청이 LLM과 Tool 호출 전에 중단되는 것을 확인합니다.
- 고객지원 업무에서도 같은 입력·Context·응답 검사를 설명할 수 있습니다.
- Lab 10의 승인 대기·결정 방식이 왜 단순 체크박스보다 안전한지 설명할 수 있습니다.

## 검증

환경 진단은 실제 통합 경로의 OpenAI·Gemma, Redis, 06 Backend와 MCP Tool 1개를
검사하며 하나라도 실패하면 종료 코드 `1`을 반환합니다.

```powershell
python -m unittest discover -s tests -v
python .\check_environment.py
```

저장 실습의 멱등성 키는 요청 내용의 지문과 함께 저장합니다. 동일한 키와 동일한 요청은 재사용하지만,
동일한 키로 다른 저장 요청을 보내면 `idempotency_key_conflict`로 차단합니다.
Provider의 429 오류는 `quota_exhausted`로 정규화하며 자동 Provider 대체는 하지 않습니다.
