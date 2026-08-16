# 남북회담 공개자료 수집

통일부 남북회담본부의 **남북합의서 해설자료** 목록(현재 84건, 9페이지)을 Playwright로 순회해 공개 첨부파일을 원본 파일명으로 저장합니다. 파일 내용은 수정하지 않으며 DB에도 적재하지 않습니다.

## 설치

Python 3.10 이상을 준비한 뒤 다음을 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## 실행

저장소 루트에서 실행합니다.

```powershell
python scripts/ingest/download_agreement_commentaries.py
```

기본 요청 간 대기시간은 1.5초입니다. 필요할 때만 더 긴 대기시간을 지정할 수 있습니다.

```powershell
python scripts/ingest/download_agreement_commentaries.py --delay 2.5
```

첨부파일은 `data/raw/agreement_commentaries/`에 저장되고, 수집 결과는 `data/raw/agreement_commentaries/download_manifest.csv`에 기록됩니다. 이미 같은 파일명이 있으면 다시 다운로드하지 않고 `already_exists`로 기록합니다. 각 파일은 확장자와 파일 크기를 확인하며, PDF/HWP/HWPX는 파일 시그니처도 확인합니다.

실패한 첨부파일은 매니페스트의 `download_status=failed`와 `error` 컬럼에 남기며, 다른 게시물 수집은 계속합니다. 스크립트는 robots.txt가 대상 경로를 차단하는 경우 실행을 중단하고, CAPTCHA·로그인·접근제한 우회는 시도하지 않습니다.

## 텍스트 추출

다운로드한 원본은 수정하지 않고 다음 명령으로 UTF-8 Markdown과 품질 Manifest를 생성합니다.

```powershell
python scripts/ingest/extract_agreement_commentaries.py
```

OLE 기반 HWP는 `pyhwp/hwp5txt`, PDF는 `pypdf`를 사용합니다. 구형 HWP V3처럼 Python 파서가 직접 지원하지 않는 파일은 공식 사이트의 공개 HTML 미리보기에서 텍스트를 가져오는 fallback을 사용하며, OCR·Chunking·Embedding·DB 적재는 수행하지 않습니다. 미리보기 요청 간 기본 대기시간은 1.5초입니다.

추출 결과는 `data/processed/agreement_commentaries/`와 `extraction_manifest.csv`에 저장됩니다.

## Phase 2 연결 점검

Phase 2에서는 Supabase, OpenRouter Chat/Embeddings, 공공데이터 API의 연결 모듈과 health endpoint만 구성합니다. 실제 연결 점검은 로컬 `.env` 설정 후 다음 명령으로 한 번 실행합니다.

```powershell
python scripts/validation/check_connections.py
```

공공데이터 API 요청 주소는 공공데이터포털 명세에 맞춰 `DATA_GO_KR_API_URL`에 설정합니다. 인증키나 응답 원문은 로그에 출력하지 않습니다. `/health/all`은 프로세스에 캐시된 최근 점검 결과만 반환하며, 데이터 적재·Embedding·RAG·Agent는 아직 수행하지 않습니다.

## Phase 4 데이터 적재

원격 Migration 적용 후 원문 데이터 batch upsert는 다음 명령으로 재실행할 수 있습니다.

```powershell
python scripts/ingest/run_phase4_ingestion.py
```

API 원문은 `data/raw/agreements/api/`, 정제 결과와 Manifest는 `data/processed/agreements/` 및 `data/processed/manifests/`에 저장됩니다. deterministic ID와 upsert를 사용하며, 현재 단계에서는 `document_chunks` 생성과 Embedding을 수행하지 않습니다. 상세 결과는 `docs/data-ingestion.md`를 참고합니다.

## 프로젝트 개요

AI 기반 남북 모의회담은 공개된 남북회담 자료와 남북합의서 해설자료를 검색 근거로 사용하는 정책 시뮬레이션 PoC입니다. AI vs AI와 사용자가 남측 대표로 참여하는 User vs AI 모드를 제공합니다. 인물과 발언은 가상이며 실제 정부 입장이나 협상 결과를 의미하지 않습니다.

## 기술 구조

- Frontend: React, Vite, TypeScript
- Backend: FastAPI, Python
- Database: Supabase PostgreSQL, pgvector
- AI/RAG: OpenRouter Chat/Embeddings, 2,468개 벡터 chunk
- Deployment target: Vercel frontend, Render API, Supabase database

## Local 실행

터미널 1:

```powershell
python -m uvicorn app.main:app --app-dir apps/api --reload --port 8000
```

터미널 2:

```powershell
cd apps/web
npm install
npm run dev
```

로컬 Vite proxy가 `/api`와 `/health`를 `localhost:8000`으로 전달합니다. 배포 시 프론트엔드에는 `VITE_API_BASE_URL`만 설정합니다.

## 회담 흐름

한 턴은 하나의 backend request로 처리됩니다. RAG 검색, Agent Structured JSON 생성, Evidence ID 검증, state 저장을 한 요청에서 수행하고, `/next/stream`은 검증된 발언을 SSE로 표시합니다. 현재 OpenRouter provider-level streaming은 Structured JSON 안정성을 위해 보류하고 있습니다.

## 환경변수

`.env.example`을 복사해 `.env`를 만들고 실제 secret을 입력합니다. `.env`와 service-role/DB/API key는 frontend bundle, 로그, Git에 넣지 않습니다. 배포 변수와 구조는 [docs/deployment.md](docs/deployment.md)를 참고합니다.

## 현재 개발 상태

Phase 9까지 완료: UI polish, 오류·로딩 UX, session_id 기반 복구, Vercel/Render 배포 manifest, local 성능 측정 스크립트, 보안 검색, 회귀 테스트.

Known limitations: provider-level token streaming, 실제 Vercel/Render 계정 배포 및 공개 URL smoke, 모바일 세부 최적화는 별도 후속 작업입니다. [docs/ui-ux.md](docs/ui-ux.md), [docs/performance.md](docs/performance.md), [docs/deployment.md](docs/deployment.md)에 현재 범위를 기록했습니다.

### Phase 9.1 배포 상태

Render와 Vercel 배포 manifest 및 환경변수 분리는 완료했습니다. 현재 workspace에는 provider CLI 인증, Git 원격, production URL이 없어 실제 배포와 production smoke는 대기 중입니다. 배포 후 `VITE_API_BASE_URL`과 Render의 `WEB_BASE_URL`을 서로의 production URL로 설정해야 합니다.
