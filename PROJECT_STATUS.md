# Project Status

## Current Summary

AI 기반 남북 모의회담 PoC는 Phase 9.1까지 완료되었습니다.

- Frontend: Vercel Production 배포 완료
- Backend: Render Production 배포 완료
- Database: Supabase PostgreSQL + pgvector 연결 완료
- RAG: 2,468개 vector chunk 적재 완료
- AI vs AI: 동작
- User vs AI: 동작
- SSE UI: 동작
- 2.5D 회담장 UI: 적용
- Production URL 확인 및 실제 프론트 화면 로딩 완료

Production URLs:

- Frontend: https://ai-interkorean-dialogue-simulator.vercel.app/
- Backend: https://ai-interkorean-dialogue-api.onrender.com

---

## Completed

### Phase 1 — Project Skeleton

- React + Vite + TypeScript Frontend 구성
- FastAPI Backend 구성
- `/health` endpoint 구현
- `.env.example`, `.gitignore`, README 작성
- Frontend build 및 Backend pytest 검증

### Phase 2 — External Connectivity

- Supabase 연결 모듈
- OpenRouter Chat / Embeddings 연결
- 공공데이터 API 연결
- `/health/db`
- `/health/openrouter`
- `/health/public-data`
- `/health/all`
- 429 / 5xx / timeout 제한적 retry 구현
- OpenRouter Embedding dimension 2048 확인

### Phase 3 — Data Schema

- 원본 데이터 구조 분석
- Mermaid ERD 작성
- Supabase Migration 작성
- `vector(2048)` 기반 pgvector schema 설계

### Phase 4 — Data Ingestion

Supabase 적재 완료:

- meetings: 933
- agreements: 79
- meeting_documents: 83
- historical_events: 1,041

남북합의서 API는 일부 filter / totalCount / payload 불일치가 확인되어 서버가 실제 반환한 데이터만 보존했습니다. 반환되지 않은 레코드는 추측하거나 생성하지 않았습니다.

### Phase 5 — Chunking + Embedding + pgvector

- documents: 2,136
- chunks: 2,468
- empty: 0
- duplicates: 0
- too long: 0
- replacement character: 0

Embedding:

```text
nvidia/nemotron-3-embed-1b:free
```

- dimension: 2048
- embedded: 2,468
- failed: 0
- document_chunks: 2,468
- embedding null: 0

Source counts:

- agreement: 175
- agreement_commentary: 319
- meeting: 933
- historical_event: 1,041

`match_document_chunks` cosine similarity 검색 함수 적용 완료.

한국어 대표 질의 4개 기준 수동 Precision@5는 약 0.90.

### Phase 6 — Agent Persona + Response Engine

협상 Agent 4개:

- south_chief: 김도현
- south_working: 박서진
- north_chief: 리명철
- north_working: 최광혁

완료:

- Persona
- Prompt
- RAG Evidence 연결
- Structured JSON
- Evidence ID validation
- 3개 Scenario
- 실제 OpenRouter Agent 6회 smoke

Phase 6 기준:

- Structured JSON: 6/6 성공
- invalid Evidence ID: 0

### Phase 7 — Simulation Engine

구현:

- Simulation State
- Turn Manager
- Phase Manager
- Speaker Selector
- Moderator
- Evaluator
- Session Memory
- AI vs AI
- DB persistence

DB tables 사용:

- simulation_sessions
- simulation_turns
- simulation_evidence
- simulation_results

### Phase 7.1 — Simulation Quality Tuning

개선:

- BREAKDOWN 편향 완화
- candidate agreement detection
- PARTIAL_AGREEMENT 조건 개선
- BREAKDOWN 조건 강화
- Moderator 조건부 호출
- Evaluator schema 안정화
- Prompt token 최적화

Prompt 평균:

```text
5,323 -> 약 3,425 tokens / turn
```

최종 smoke:

| Scenario | Rounds | Result |
|---|---:|---|
| separated_families | 6 | AGREEMENT |
| transport_cooperation | 6 | BREAKDOWN |
| military_tension | 6 | PARTIAL_AGREEMENT |

Moderator 실제 호출: 6회  
Evaluator fallback: 0회

### Phase 8 — User vs AI + SSE + 2.5D UI

완료:

- User vs AI API
- 사용자 발언 원문 저장
- 북측 AI 응답
- SSE frontend parser
- 비스트리밍 fallback
- 남측 3명 / 북측 3명 캐릭터
- speaking / thinking / waiting 상태
- Analysis Panel
- Evidence Panel
- Result View

검증:

- AI vs AI browser smoke: PASS
- User vs AI browser smoke: PASS
- pytest: 15 passed
- frontend build: PASS

### Phase 9 — UI Polish + Performance

완료:

- 2.5D 회담장 depth 개선
- 현재 발언자 강조
- 긴 발언 가독성 개선
- SpeechBubble 축약
- `전체 발언 →` UX
- `회담 현황 / 현재 발언` 탭
- 현재 발언 원문 3~5문단 표시
- Evidence 최대 3건 표시
- 내부 Evidence ID(E1/E2/E3) 사용자 노출 제거 방향 적용
- source_type 사용자용 한글 label 적용 방향
- loading / error UX
- session_id 기반 복구
- 1280×720 / 1440×900 / 1920×1080 검증
- footer `Made by Ch.` 시인성 개선

성능 로컬 측정:

- health: 약 223.8ms
- simulation create: 약 165.8ms
- warm turn: 약 47.2초

주요 병목은 OpenRouter 응답 지연.

### Phase 9.1 — Production Deployment

#### GitHub

- Repository: `swainy195/ai-interkorean-dialogue-simulator`
- branch: `main`
- Git remote / push 완료
- `.env` 미추적
- API key / DB password / Supabase secret pattern 미검출
- 대용량 `embedded_chunks.jsonl`은 로컬 유지, Git 추적 제외

#### Render

Backend Production 배포 완료.

```text
https://ai-interkorean-dialogue-api.onrender.com
```

- Python 3
- Root Directory: `apps/api`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Region: Singapore
- Free Instance
- Health Check: `/health`
- Deploy succeeded / Live 확인

#### Vercel

Frontend Production 배포 완료.

```text
https://ai-interkorean-dialogue-simulator.vercel.app/
```

- Framework: Vite
- Root Directory: `apps/web`
- Frontend env는 `VITE_API_BASE_URL`만 사용
- Secret frontend 노출 없음
- Production 화면 실제 로딩 확인

#### CORS

- Render `WEB_BASE_URL`을 Vercel Production origin 기준으로 구성
- wildcard `*` 미사용

---

## AI Model Status

### Production Chat Model

```text
google/gemma-3-27b-it
```

Baseline:

- 6/6 success
- Structured JSON 6/6
- invalid Evidence ID 0
- 평균 latency 약 15.3초
- reported cost 약 0.00224241 / 6 calls

### Embedding Model

```text
nvidia/nemotron-3-embed-1b:free
```

### Free Chat Model Benchmark

공개 사용자 배포 비용 절감을 위해 무료 후보를 검증했습니다.

| Model | Structured JSON | Avg Latency | Verdict |
|---|---:|---:|---|
| google/gemma-4-26b-a4b-it:free | 6/6 | 약 37.0초 | 조건부 PASS |
| nvidia/nemotron-nano-9b-v2:free | 0/2 | 약 22.7초 | FAIL |
| nvidia/nemotron-3-super-120b-a12b:free | 0/2 | 약 10.8초 | FAIL |
| openai/gpt-oss-20b:free | 0/6 | 약 45.9초 | FAIL |

현재 Production은 안정성과 응답속도를 우선해 `google/gemma-3-27b-it`을 유지합니다.

---

## In Progress

- Production 환경 장기 안정성 확인
- 실제 사용자 접근 시 rate limit / session limit 검토
- 무료 Chat Model staged rollout 가능성 검토
- provider-level streaming 대신 현재 SSE 구조 유지 여부 최종 판단
- 발표용 Demo Scenario 및 시연 흐름 정리

---

## Known Limitations

- 정식 labeled RAG evaluation set 없음
- Agent 품질 평가는 smoke test 중심
- 회담 결과는 LLM 응답과 deterministic heuristic에 의존
- OpenRouter latency 변동 가능
- Render Free Instance cold start 가능
- provider-level token streaming 미적용
- 일부 HWP 추출 과정에서 표·레이아웃 정보 손실 가능
- 공공데이터 남북합의서 API의 filter / totalCount / payload 불일치 존재
- pytest 실행 시 Starlette/httpx deprecation warning 1건

---

## Test Status

- Backend pytest: 15 passed
- Frontend build: PASS
- AI vs AI: PASS
- User vs AI: PASS
- SSE: PASS
- Evidence UI: PASS
- terminal branch fixture: PASS
- RAG embedding: 2,468 / 2,468
- embedding null: 0

---

## Next Step

### Phase 10 — Final QA + Demo Scenario + Presentation Readiness

예정:

- Production smoke 최종 정리
- 공개 사용자용 사용량 보호장치 검토
- Demo Scenario 고정
- 시연 순서 및 발표 포인트 정리
- Final QA
- 발표용 시연 영상 준비
