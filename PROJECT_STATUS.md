# Project Status

## Completed

- Phase 1 프로젝트 골격
- React + Vite + TypeScript 기본 Home 화면
- FastAPI `/health` endpoint 및 local Vite CORS
- Frontend build와 Backend pytest 검증
- 실제 Uvicorn 실행 후 `GET /health` 200 OK 확인
- `.env.example`, `.gitignore`, README 초기 개발 안내
- 기존 공개 원본·가공 데이터 보존
- Phase 2 연결 모듈: Supabase, OpenRouter Chat/Embeddings, 공공데이터 API
- `/health/db`, `/health/openrouter`, `/health/public-data`, `/health/all`
- 연결 재시도 정책(429/5xx/timeout, 최대 2회 재시도) 및 mock 테스트
- `scripts/validation/check_connections.py`
- Phase 2 외부 서비스 최종 연결 검증 완료
- 공공데이터 `getNktalkmng` 샘플 조회 성공: 10건, totalCount 18
- OpenRouter Embeddings dimension 2048 확인
- `/health/all` → `ok`
- Phase 3 원본 데이터 구조 분석 및 통합 스키마 설계
- Phase 3 Mermaid ERD 및 Supabase Migration 작성
- `vector(2048)` 컬럼과 비파괴 제약·인덱스 정적 검증
- Phase 4 원격 Migration 적용 및 실제 스키마 검증
- Phase 4 전체 원문 batch upsert 및 idempotent 재실행 확인
- Phase 4 적재 Manifest·품질 검증 완료
- Phase 4.1 남북합의서 API 무결성 최종 검증 완료: 날짜/thema 단독 조회는 0건, 기존 동작 조건에서는 thema=1/2 모두 totalCount 80·payload 79이며 실제 thema 값이 혼재
- Phase 5 deterministic chunk 생성·품질검증 완료: 2,136 documents, 2,468 chunks
- Phase 5 OpenRouter Embedding 완료: `nvidia/nemotron-3-embed-1b:free`, dimension 2048, 실패 0
- Phase 5 `document_chunks` batch upsert 완료: 2,468행, embedding null 0
- Phase 5 `match_document_chunks` cosine 검색 함수 및 한국어 4개 질의 smoke test 완료
- Phase 6 4개 협상 Agent Persona·3개 Scenario·공통 Prompt 구현
- Phase 6 RAG evidence 연결·Structured JSON·Evidence ID validation 구현
- Phase 6 실제 OpenRouter Agent 6회 및 FastAPI endpoint smoke test 완료
- Phase 7 Simulation migration 및 4개 persistence table 적용
- Phase 7 Moderator, Evaluator, State/Phase/Speaker/Turn Manager 및 AI_VS_AI API 구현
- Phase 7 separated_families 6턴, transport_cooperation 4턴, military_tension 4턴 실제 smoke 완료
- Phase 7 Evidence/Turn/Result DB 저장 및 terminal next 차단 검증 완료
- Phase 7.1 종료 휴리스틱 튜닝 및 round transition replay 완료
- Phase 7.1 최종 smoke: separated_families AGREEMENT, transport BREAKDOWN, military PARTIAL_AGREEMENT
- Phase 7.1 Moderator 조건부 실제 호출 6회(회담당 2회), Evaluator schema fallback 0회
- Phase 7.1 prompt 평균 3,425 tokens/turn으로 Phase 7 대비 최적화
- Phase 8 User vs AI 모드, 사용자 발언 저장 및 북측 AI 응답 연결
- Phase 8 SSE streaming endpoint/frontend parser와 비스트리밍 fallback 구현
- Phase 8 반입체 회담장 UI, 6명 캐릭터 상태, 분석 패널, 근거자료, 결과 카드 구현
- Phase 8 브라우저/API smoke: AI vs AI 및 User vs AI 실제 호출 확인
- Phase 8 pytest 15 passed, frontend build 성공
- Phase 9 UI polish: 긴 발언 접기/확장, compact Evidence, 정책형 단계 표시, loading/error UX, session_id 복구
- Phase 9 1280x720·1440x900·1920x1080 브라우저 레이아웃 검증 및 현재 발언자 표시 확인
- Phase 9 local 성능 측정: health 223.8ms, create 165.8ms, warm turn 47,198.5ms, Evidence 3건
- Phase 9 Vercel/Render 배포 manifest 및 production 환경변수 분리 문서 작성
- Phase 9 secret pattern 검색 결과 없음, pytest 15 passed, frontend build 성공
- Phase 9.1 배포 전 검증: Vercel/Render CLI 인증·Git 원격·production URL 없음 확인

## In Progress

- Phase 5 retrieval smoke test는 수동 Precision@5 약 0.90인 초기 검증이며 정식 labeled evaluation set은 없음
- Phase 6 Agent 6회 smoke test는 정식 협상 품질 평가셋이 아니며, 사실성 전체를 자동 보증하지 않음
- Phase 7.1 branch 결과는 LLM 응답과 deterministic 휴리스틱에 의존하며, 정식 협상 품질 평가셋은 아직 없음
- Phase 8 SSE는 현재 완성된 provider 응답을 서버에서 조각내 전달하며, upstream token streaming은 아직 미적용
- Phase 9 warm turn은 47.2초로 OpenRouter 응답 지연의 영향을 크게 받음. provider-level streaming은 Structured JSON 안정성 때문에 보류
- 실제 Vercel/Render 계정 배포와 production URL smoke는 provider 계정 권한 및 공개 URL이 필요함
- Phase 9.1은 외부 배포 권한 부재로 배포 및 production smoke 미완료

## Pending

- Phase 9: UI Polish, 성능 최적화, 배포 검증

## Issues

- pytest 실행 시 Starlette/httpx deprecation warning 1건이 있으나 테스트는 통과함
- Supabase: HTTP 200 OK
- OpenRouter Chat: HTTP 200 OK, 응답 생성 성공
- OpenRouter Embeddings: 공식 모델 목록에서 `nvidia/nemotron-3-embed-1b:free` 확인 후 HTTP 200, dimension 2048
- 공공데이터 API: 공식 operation 및 샘플 파라미터로 HTTP 200, resultCode 0
- 파라미터 제거 검증: keyword/thema/country는 호출 가능, 날짜 조건 제거는 오류 코드 11
- Phase 4 API 6개 theme partition: raw 474 item, unique agreements 79행
- API partition `totalCount=480` 대비 실제 payload 474건. page size·경계값 변경에도 서버가 일부 item을 반환하지 않아 원문 누락 가능성을 보존하고 추가 추측 수집은 중단
- Phase 4.1 엄격 검증에서도 날짜-only 및 thema-only 요청은 totalCount/payload 0. 기존 keyword/country 조건의 thema filter는 실제 값이 혼재하여 서버 필터 결함 가능성. 80번째 record는 추측하지 않고 agreements 79건 유지
- Phase 4 meetings 933행, meeting_documents 83행, historical_events 1,041행
- document_chunks는 의도적으로 0행

## Phase 1 Verification

- Frontend: `npm run build` 성공
- Frontend dev server: `http://127.0.0.1:5173/` → `200 OK`
- Backend: `pytest` 성공 (1 passed)
- Health: `GET http://127.0.0.1:8000/health` → `200 OK`

## Next Step

Phase 9 deployment gate: Vercel/Render 계정 연결 후 production URL smoke를 수행한 뒤 Phase 10으로 진행
