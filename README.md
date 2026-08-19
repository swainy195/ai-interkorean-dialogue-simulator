# AI 기반 남북 모의회담

공개된 남북회담·남북합의서·공식 해설자료를 RAG로 연결하고, 다중 AI Agent가 현재 시점의 가상 남북회담을 진행하는 정책 시뮬레이션 PoC입니다.

> **Live Demo**: https://ai-interkorean-dialogue-simulator.vercel.app/  
> **Backend API**: https://ai-interkorean-dialogue-api.onrender.com  
> **GitHub**: https://github.com/swainy195/ai-interkorean-dialogue-simulator

---

## 1. 프로젝트 개요

이 프로젝트의 목표는 과거 회담을 단순 재현하는 것이 아니라, 공개된 공식자료를 근거로 **현재 시점의 가상 남북회담을 AI가 시뮬레이션**하도록 만드는 것입니다.

핵심 원칙은 다음과 같습니다.

- 공식 공개자료 중심 RAG
- 실제 인물 대신 가명·합성 Persona 사용
- AI 발언과 역사적 사실의 구분
- Evidence ID 검증을 통한 근거 연결
- AI vs AI 및 사용자 참여형 회담 지원
- 결과를 실제 남북협상의 예측값으로 해석하지 않음

현재 서비스는 세 가지 의제를 제공합니다.

1. 이산가족 상봉 재개
2. 철도·도로 및 물류 협력
3. 군사적 긴장완화

관계 상황은 `관계 개선 / 보통 / 긴장`으로 설정할 수 있습니다.

---

## 2. 주요 기능

### AI vs AI

남측과 북측 협상 Agent가 공식자료를 검색하고, 제안·반박·양보·절충을 반복하며 회담을 진행합니다.

### User vs AI

사용자가 남측 대표 역할로 직접 발언하고, AI 북측 대표가 현재 회담 상태와 RAG Evidence를 바탕으로 응답합니다.

### RAG 기반 근거 연결

각 Turn마다 현재 의제·협상 단계·미합의 쟁점·상대 발언을 기반으로 관련 자료를 검색합니다.

- Vector Search Top 10
- 동일 문서 최대 2개
- 최종 Prompt에는 기본 3개 Evidence 사용
- Evidence content 최대 약 750자
- Agent가 사용한 Evidence ID 검증

사용자 UI에서는 내부 `E1`, `E2`, `E3` 식별자 대신 실제 자료 제목과 자료 유형을 표시하도록 구성합니다.

### Simulation Engine

회담은 단순 채팅이 아니라 명시적인 State를 갖는 시뮬레이션으로 동작합니다.

- Phase Manager
- Turn Manager
- Speaker Selector
- Moderator
- Evaluator
- Session Memory
- Agreement / Partial Agreement / Breakdown 판정

한 Turn은 하나의 Backend Request로 처리합니다.

```text
Frontend
  -> POST /api/v1/simulations/{id}/next
  -> State Load
  -> RAG Search
  -> Agent Prompt
  -> OpenRouter
  -> Structured JSON Validation
  -> State Update
  -> Evidence / Turn / Result Persistence
  -> Response
```

---

## 3. Agent 구성

화면에는 남측 3명, 북측 3명 총 6명의 가상 인물이 등장합니다.

실제 LLM 협상 Agent는 4명입니다.

| 구분 | 이름 | 역할 |
|---|---|---|
| 남측 수석대표 | 김도현 | 원칙·방향·핵심 제안·절충 |
| 남측 실무대표 | 박서진 | 일정·절차·실행·세부 조건 |
| 북측 단장 | 리명철 | 조건부 수용·역제안·우선사항 |
| 북측 실무대표 | 최광혁 | 세부 조건·수정안·실무 대응 |

추가 백그라운드 Agent:

- Moderator: Phase·쟁점·반복·종료조건 판단
- Evaluator: 회담 종료 후 합의사항·미합의사항·후속과제 정리

배석대표 2명은 UI용 가상 캐릭터이며 별도 LLM Agent가 아닙니다.

---

## 4. 회담 Phase

```text
OPENING
  -> AGENDA
  -> PROPOSAL
  -> RESPONSE
  -> ISSUE_IDENTIFICATION
  -> NEGOTIATION
  -> COMPROMISE
  -> FINALIZATION
```

종료 상태:

- `AGREEMENT`
- `PARTIAL_AGREEMENT`
- `BREAKDOWN`

UI에서는 raw enum 대신 `개회 / 의제 확인 / 제안 / 입장 확인 / 쟁점 확인 / 협상 / 절충 / 합의안 정리`로 표시합니다.

`agreement_level`, `tension_level`은 현실 확률이 아니라 **시뮬레이션 내부 상태값**입니다.

---

## 5. 데이터

### 공개 데이터 원천

- 통일부 남북회담 정보
- 통일부 남북관계관리단 연도별 회담현황
- 통일부 남북관계관리단 개최회담관리
- 통일부 남북이산가족 연표
- 통일부 남북합의서 조회 API
- 남북합의서 해설자료

### 적재 현황

| 테이블 | 건수 |
|---|---:|
| meetings | 933 |
| agreements | 79 |
| meeting_documents | 83 |
| historical_events | 1,041 |
| document_chunks | 2,468 |

Chunk source별 건수:

| source_type | chunks |
|---|---:|
| agreement | 175 |
| agreement_commentary | 319 |
| meeting | 933 |
| historical_event | 1,041 |

총 2,136개 문서에서 2,468개 Chunk를 생성했으며, 모든 RAG Chunk는 2048차원 Embedding을 보유합니다.

### 남북합의서 API 주의사항

공공데이터 API는 일부 검색 조건에서 `totalCount`와 실제 payload 수가 일치하지 않는 문제가 확인되었습니다. 서버가 실제 반환한 79건만 적재했으며, 누락 가능성이 있는 레코드를 임의로 추측하거나 생성하지 않았습니다.

---

## 6. RAG

Embedding Model:

```text
nvidia/nemotron-3-embed-1b:free
```

- Dimension: 2048
- Vector DB: Supabase pgvector
- Similarity: cosine similarity
- 검색 함수: `match_document_chunks`
- 한국어 4개 대표 질의 수동 Precision@5: 약 0.90

대표 검증 질의:

- 이산가족 상봉 재개와 관련된 과거 합의와 회담
- 남북 철도·도로 연결 공동조사 및 협력 사례
- 군사적 긴장완화와 우발적 충돌 방지 합의
- 남북 고위급회담의 주요 논의 내용

---

## 7. AI 모델

### 현재 Chat Model

```text
google/gemma-3-27b-it
```

Phase 6 기준 Structured JSON 6/6 성공, invalid Evidence ID 0건으로 현재 Production 기본 모델로 사용합니다.

### 무료 모델 Benchmark

공개 배포 비용을 낮추기 위해 무료 모델을 별도 검증했습니다.

| Model | Structured JSON | 평균 지연 | 결과 |
|---|---:|---:|---|
| google/gemma-4-26b-a4b-it:free | 6/6 | 약 37.0초 | 조건부 PASS |
| nvidia/nemotron-nano-9b-v2:free | 0/2 | 약 22.7초 | FAIL |
| nvidia/nemotron-3-super-120b-a12b:free | 0/2 | 약 10.8초 | FAIL |
| openai/gpt-oss-20b:free | 0/6 | 약 45.9초 | FAIL |

현재는 응답 안정성과 지연시간을 고려하여 `google/gemma-3-27b-it`을 유지하고 있습니다.

---

## 8. UI / UX

Frontend는 전통적인 Chat UI 대신 **2.5D 정책 시뮬레이션 회담장** 형태로 구성했습니다.

주요 UI 요소:

- 남측 3명 / 북측 3명 가상 캐릭터
- `idle / thinking / speaking / waiting` 상태
- 현재 발언자 강조
- 짧은 SpeechBubble
- `회담 현황 / 현재 발언` 탭
- 전체 발언 원문과 Evidence 동시 확인
- 현재 쟁점·합의·미합의 항목 표시
- 결과 화면: 합의 / 부분합의 / 결렬

SpeechBubble은 긴 AI 발언 전체를 표시하지 않고 약 120~180자, 최대 3문장 수준의 핵심 내용만 보여줍니다. 전체 원문과 근거자료는 오른쪽 `현재 발언` 탭에서 확인할 수 있습니다.

검증 해상도:

- 1280×720
- 1440×900
- 1920×1080

---

## 9. 기술 구조

```text
Vercel
React + Vite + TypeScript
        |
        v
Render
FastAPI + Python
        |
        +--> OpenRouter Chat
        +--> OpenRouter Embeddings
        |
        v
Supabase
PostgreSQL + pgvector
```

### Stack

- Frontend: React, Vite, TypeScript
- Backend: FastAPI, Python
- Database: Supabase PostgreSQL
- Vector Search: pgvector
- Chat / Embeddings: OpenRouter
- Frontend Deployment: Vercel
- Backend Deployment: Render
- Source Control: GitHub

---

## 10. Production Deployment

### Frontend

Vercel:

https://ai-interkorean-dialogue-simulator.vercel.app/

### Backend

Render:

https://ai-interkorean-dialogue-api.onrender.com

Health Check:

```text
/health
/health/db
/health/openrouter
/health/public-data
/health/all
```

Render Free Instance는 비활성 상태가 지속되면 spin down될 수 있어 첫 요청에 Cold Start 지연이 발생할 수 있습니다.

---

## 11. API

주요 Simulation API:

```text
POST /api/v1/simulations
POST /api/v1/simulations/{id}/next
POST /api/v1/simulations/{id}/user-turn
GET  /api/v1/simulations/{id}
GET  /api/v1/simulations/{id}/state
GET  /api/v1/simulations/{id}/evidence
GET  /api/v1/simulations/{id}/result
```

Agent 검증용 API:

```text
POST /api/v1/agents/respond
```

SSE endpoint는 현재 Backend에서 검증 완료된 응답을 분할 전송합니다. Structured JSON 및 Evidence ID 안정성을 우선하여 OpenRouter provider-level token streaming은 현재 적용하지 않았습니다.

---

## 12. Local 실행

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r apps/api/requirements.txt
python -m uvicorn app.main:app --app-dir apps/api --reload --port 8000
```

### Frontend

```powershell
cd apps/web
npm install
npm run dev
```

개발 기본 주소:

```text
Frontend: http://localhost:5173
Backend : http://localhost:8000
```

---

## 13. 환경변수

`.env.example`을 참고해 Backend Secret을 설정합니다.

Backend:

```text
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_DB_URL
OPENROUTER_API_KEY
OPENROUTER_CHAT_MODEL
OPENROUTER_EMBEDDING_MODEL
DATA_GO_KR_API_KEY
DATA_GO_KR_API_URL
WEB_BASE_URL
```

Frontend에는 Secret을 넣지 않습니다.

```text
VITE_API_BASE_URL
```

`.env`, Service Role Key, DB Password, OpenRouter API Key 등은 Git에 commit하지 않습니다.

---

## 14. 프로젝트 구조

```text
apps/
  web/                  # React + Vite Frontend
  api/                  # FastAPI Backend

data/
  raw/                  # 원본 공개자료
  processed/            # 정제·Chunk 산출물

scripts/
  ingest/               # 데이터 수집·적재
  embeddings/           # Chunk / Embedding
  validation/           # 품질·RAG·Simulation 검증

supabase/
  migrations/           # DB / RAG / Simulation migrations

docs/
  data-ingestion.md
  data-model.md
  data-schema-analysis.md
  rag.md
  agents.md
  simulation.md
  ui-ux.md
  deployment.md
  performance.md

README.md
PROJECT_STATUS.md
```

대용량 생성 산출물인 `data/processed/chunks/embedded_chunks.jsonl`은 로컬에 유지하되 Git 추적에서는 제외합니다.

---

## 15. 테스트 및 검증

현재 주요 검증 결과:

- Backend pytest: 15 passed
- Frontend production build: PASS
- RAG Embedding: 2,468 / 2,468 성공
- embedding null: 0
- Agent Structured JSON: PASS
- invalid Evidence ID: 0
- AI vs AI browser smoke: PASS
- User vs AI browser smoke: PASS
- SSE UI: PASS
- 3개 terminal branch fixture: PASS

Phase 7.1 실제 회담 결과:

| Scenario | Rounds | Result |
|---|---:|---|
| 이산가족 | 6 | AGREEMENT |
| 철도·도로 | 6 | BREAKDOWN |
| 군사 긴장완화 | 6 | PARTIAL_AGREEMENT |

이 결과는 실제 남북협상 결과의 예측이 아니라 Simulation Engine branch 검증 결과입니다.

---

## 16. 성능

Phase 7.1 Prompt 최적화:

```text
평균 Prompt Tokens / Turn
5,323 -> 약 3,425
```

적용 내용:

- Evidence 5개 → 기본 3개
- Evidence 본문 최대 약 750자
- 최근 2개 발언 중심 Context
- 전체 State 대신 핵심 State만 Prompt에 전달

Local Phase 9 측정에서 warm turn은 약 47초까지 관찰되었으며, 주요 병목은 OpenRouter 응답 지연입니다. 모델·Provider 상태에 따라 실제 응답시간은 달라질 수 있습니다.

---

## 17. Safety / Disclaimer

본 서비스는 공개된 남북회담 기록과 공식자료를 활용한 **가상 회담 시뮬레이션**입니다.

- 등장인물은 모두 가상의 인물입니다.
- AI 생성 발언은 실제 대한민국 정부, 북한 당국 또는 실제 인물의 공식 입장을 의미하지 않습니다.
- 역사적 사실과 현재 Simulation의 가정 및 AI 생성 제안을 구분합니다.
- Simulation 결과는 실제 남북협상의 성공 가능성이나 미래 결과를 예측하지 않습니다.
- 공개자료에 없는 내용을 역사적 사실로 단정하지 않도록 Evidence 기반 검증을 적용합니다.

---

## 18. Known Limitations

- 정식 labeled RAG 평가셋은 아직 없음
- Agent 품질 평가는 현재 smoke test 중심
- LLM 응답과 deterministic 휴리스틱에 따라 회담 결과가 달라질 수 있음
- 무료 Render Instance의 Cold Start 가능성
- OpenRouter 응답 지연 가능성
- provider-level token streaming 미적용
- 일부 HWP 문서는 추출 과정에서 표·레이아웃 정보가 손실될 수 있음
- 공공데이터 남북합의서 API의 count/filter 불일치 문제 존재

---

## 19. 개발 단계

```text
Phase 1   Project Skeleton
Phase 2   External Connectivity
Phase 3   Data Schema
Phase 4   Data Ingestion
Phase 4.1 Agreement API Integrity Check
Phase 5   Chunking + Embedding + pgvector
Phase 6   Agent Persona + Response Engine
Phase 7   Simulation Engine
Phase 7.1 Simulation Quality Tuning
Phase 8   User vs AI + SSE + 2.5D UI
Phase 9   UI Polish + Performance
Phase 9.1 Production Deployment
```

현재 Vercel Frontend와 Render Backend가 실제 Production 환경에 배포되어 있습니다.

---

## 20. 다음 단계

- Production smoke 및 장기 안정성 확인
- 공개 사용자 대상 사용량·비용 보호장치 검토
- 무료 Chat Model staged rollout 검토
- Final QA
- Demo Scenario 고정 및 발표 시나리오 작성
- 발표용 시연 영상 제작

---

## License / Data

본 프로젝트는 PoC 및 연구·정책 시뮬레이션 목적으로 개발되었습니다. 외부 공개자료의 저작권과 이용조건은 각 원천기관의 정책을 따릅니다.
