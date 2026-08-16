# AI 기반 남북 모의회담 PoC 종합 기획서

- 문서 버전: v2.0
- 기준일: 2026-08-16
- 프로젝트명: **AI 기반 남북 모의회담**
- 개발 기간: 2주 PoC
- 운영 원칙: 무료 범위 내 구축 및 배포
- AI/RAG: **OpenRouter Chat API + OpenRouter Embeddings API**
- DB/Vector DB: **Supabase PostgreSQL + pgvector**
- Frontend: **React + Vite + TypeScript**
- Backend: **FastAPI**
- 배포: **Vercel Free + Render Free**

---

## 1. 프로젝트 개요

본 프로젝트는 통일부 및 공공데이터포털 등을 통해 공개된 남북회담 기록, 남북합의서, 회담별 자료, 남북합의서 해설자료, 이산가족 연표 등을 활용하여 **현재 시점의 가상 남북회담을 AI 에이전트들이 수행하는 정책 시뮬레이션 서비스**를 구축하는 것을 목적으로 한다.

단순 질의응답형 챗봇이 아니라 각 AI 에이전트가 서로 다른 역할, 목표, 협상 성향, 우선순위, 양보 가능 범위와 제한조건을 가지고 제안·반박·실무협의·절충·합의 또는 결렬에 이르는 회담 흐름을 수행한다.

사용자는 두 가지 모드를 이용한다.

1. **AI vs AI**: 남측·북측 AI Agent들이 자동으로 회담 진행
2. **사용자 vs AI**: 사용자가 남측 대표로 참여하여 AI 북측 대표와 협상

서비스 화면은 전통적인 픽셀게임 방식이 아니라 **세련된 2.5D/아이소메트릭 회담장 + 정책 대시보드 UI**를 지향한다.

---

## 2. 한 줄 정의

> **공개된 남북회담 및 남북합의서 데이터를 RAG로 활용하여, 가명으로 구성된 남·북 AI 에이전트들이 현재 시점의 가상 남북회담을 진행하고 사용자가 직접 협상에도 참여할 수 있는 AI 정책 시뮬레이션 서비스**

---

## 3. 핵심 기술 가치

```text
남북회담 공개데이터
        +
OpenRouter Embeddings
        +
Supabase pgvector
        +
RAG
        +
가명 복합 Persona
        +
Multi-Agent
        +
Simulation Engine
        +
2.5D UI/UX
```

핵심 가치는 **과거에 축적된 남북회담 데이터를 현재의 가상 협상 경험으로 전환하는 것**이다.

---

## 4. 기본 원칙

### 4.1 시간 배경
- 현재 시점
- 실제 현재 남북관계를 그대로 재현하거나 미래를 예측하지 않음
- 사용자 또는 시스템이 선택한 **가상 Scenario Context**를 기반으로 함

예시:

```text
시점: 현재
가상 상황: 남북 간 실무접촉이 재개되었다고 가정
의제: 이산가족 상봉 재개
남측 목표: 정례적 상봉 및 생사확인 체계 마련
북측 목표: 상호 관심사항 병행 논의
회담 목표: 실무협의 합의 도출
```

### 4.2 실제 인물 사용 원칙
- 실존 인물 이름은 사용하지 않음
- 여러 공개 회담자료에서 확인되는 역할·협상 특성을 참고해 **가명의 복합 Persona** 생성
- 특정 실존인물을 그대로 재현하지 않음

예:
- 남측 수석대표: 김도현(가명)
- 남측 실무대표: 박서진(가명)
- 북측 단장: 리명철(가명)
- 북측 실무대표: 최광혁(가명)

### 4.3 사실과 AI 생성 구분
UI와 데이터에서 아래 세 종류를 명확히 구분한다.

- **Historical Fact**: 공식자료에서 확인되는 사실
- **Scenario Assumption**: 현재 가상회담을 위한 조건
- **AI Generated Negotiation**: AI가 생성한 가상 제안·반박·절충안

---

## 5. 1차 PoC 의제

### 5.1 이산가족 상봉 재개
- 인도적 의제
- 관련 과거 회담 및 연표 풍부
- 사용자 이해도가 높음

### 5.2 철도·도로 및 물류 협력
- 경제협력형 의제
- 공동조사·실무협의·단계적 추진 등 협상 구조 구현에 적합

### 5.3 군사적 긴장완화
- 양측 입장 차이가 뚜렷함
- Red Line, 양보, 부분합의·결렬 시연에 적합

관계 상황은 다음 3개를 제공한다.

```text
관계 개선
보통
긴장 고조
```

---

## 6. 회담 모드

### 6.1 AI vs AI

```text
Scenario 선택
→ RAG 검색
→ 남측 제안
→ 북측 대응
→ 실무대표 개입
→ 쟁점 갱신
→ 협상·절충
→ 합의 / 부분합의 / 결렬
```

### 6.2 사용자 vs AI
- 사용자가 남측 대표로 참여
- 자유 입력
- 선택적으로 AI 추천 발언 제공
- 사용자 발언도 Negotiation State에 반영

1차 PoC 제외:
- 사용자 북측 대표
- 다중 사용자
- 실시간 네트워크 회담

---

## 7. 화면상 회담 인원

UI에는 **남측 3명 + 북측 3명 = 총 6명**이 등장한다.

### 남측
1. 수석대표
2. 실무대표
3. 배석대표

### 북측
1. 단장
2. 실무대표
3. 배석대표

배석대표는 1차 PoC에서는 별도 LLM Agent가 아니라 시각적 캐릭터로 활용한다.

---

## 8. 실제 AI Agent 구성

실제 AI Agent는 총 **6개**다.

### 협상 Agent 4개
1. 남측 수석대표 Agent
2. 남측 실무대표 Agent
3. 북측 단장 Agent
4. 북측 실무대표 Agent

### 백그라운드 Agent 2개
5. 회담 진행 Agent
6. 평가 Agent

정리:

```text
화면 등장 캐릭터: 6명
실제 협상 발언 Agent: 4명
백그라운드 Agent: 2명
총 AI Agent: 6개
```

---

## 9. Agent별 역할

### 남측 수석대표
- 큰 협상 방향
- 핵심 제안
- 정책적 원칙
- 최종 절충안

### 남측 실무대표
- 일정
- 절차
- 실행계획
- 실무협의
- 구체 조건

### 북측 단장
- 원칙적 대응
- 주요 요구사항
- 조건부 수용
- 역제안

### 북측 실무대표
- 실무 조건
- 절차적 요구
- 구체적 수정안
- 선결조건

### 진행 Agent
- 현재 Phase 판단
- 발언 순서
- 반복 감지
- 쟁점 갱신
- 조기 종료 판단

### 평가 Agent
- 회담 결과 요약
- 양측 핵심 입장
- 합의·미합의 사항
- 근거 활용 평가
- 후속 협상 쟁점

---

## 10. Persona 설계 원칙

Persona는 단순 말투가 아니라 협상 행동 변수로 구성한다.

```yaml
name: 김도현
side: south
role: 수석대표

negotiation_style:
  - 실무적
  - 단계적 합의 선호
  - 대화 지속 중시

priority:
  - 실무협의체 구성
  - 지속 가능한 합의

acceptable_concession:
  - 일정 조정
  - 단계적 이행

red_line:
  - 핵심 정책 원칙 훼손 금지
```

---

## 11. 확보 데이터 현황

### 11.1 CSV 4종 확보 완료

1. **통일부_남북회담 정보**
   - 회담 Master
   - 회담명, 분야, 일자, 장소

2. **통일부_남북관계관리단_연도별회담현황데이터관리**
   - 회담 상세 맥락
   - 주요 논의사항, 결과
   - RAG 보조

3. **통일부_남북관계관리단_개최회담관리**
   - 회담 기간
   - 회담수, 방문수
   - Master 보완

4. **통일부_남북이산가족 연표**
   - 이산가족 Scenario
   - 역사적 Context

원본 파일명은 변경하지 않고 `data/raw/`에 보관한다.

### 11.2 남북합의서 해설자료 확보 완료

```text
전체 게시물: 84
첨부파일 존재: 83
첨부파일 없음: 1
다운로드 성공: 83
실패: 0

HWP: 82
PDF: 1
```

원본:
`data/raw/agreement_commentaries/`

Manifest:
`data/raw/agreement_commentaries/download_manifest.csv`

### 11.3 해설자료 텍스트 추출 완료

```text
전체 원본: 83
추출 성공: 71
경고: 12
실패: 0
Markdown 생성: 83

평균 문자 수: 2,973.1
최소: 477
최대: 30,527
깨진 문자: 0
빈 문서: 0
```

추출 방식:
- pyhwp-hwp5txt: 35
- pypdf: 1
- 공식 HTML 미리보기 fallback: 47

경고 12건은 주로 제목 인식 실패로, 본문 추출 실패는 아님.

### 11.4 남북합의서 본문 API
- `통일부_남북관계 남북합의서 조회 서비스`
- API 인증키 확보 완료
- 환경변수: `DATA_GO_KR_API_KEY`
- API Key 하드코딩 금지

수집 항목:
- 개최회담
- 회담분야
- 국가
- 지역
- 시설
- 제목
- 내용
- 회담일자
- 파일명
- 원문 URL

---

## 12. 원본·가공본·DB 관리 원칙

```text
원본
data/raw/
→ 원본 파일명 유지

가공본
data/processed/
→ 내부 표준명 사용

DB
→ 서비스 구조에 맞는 표준 테이블명
```

이 구조를 통해 provenance(출처 추적성)를 유지한다.

---

## 13. RAG 전체 구조

```text
남북회담 공개데이터
        ↓
정제
        ↓
Document Chunking
        ↓
OpenRouter Embeddings API
        ↓
Embedding Vector
        ↓
Supabase PostgreSQL + pgvector
        ↓
Vector Similarity Search
        ↓
Metadata Filter
        ↓
Top Evidence
        ↓
OpenRouter Chat API
        ↓
Agent Response
```

---

## 14. RAG Data Layer

### Layer 1 — 회담 기본정보
- 남북회담 정보
- 개최회담관리
- 연도별회담현황

### Layer 2 — 협상 원문
- 남북합의서 본문
- 회담 상세자료
- 합의문·공동보도문

### Layer 3 — 공식 해설
- 남북합의서 해설자료

### Layer 4 — 역사·상황
- 이산가족 연표
- 필요 시 향후 북한 약사·공식 정책자료 추가

---

## 15. RAG 검색 우선순위

```text
1. 현재 의제와 직접 관련된 남북합의서
2. 관련 회담 원문
3. 공식 해설자료
4. 과거 유사 회담
5. 역사·상황자료
```

---

## 16. Chunking 원칙

단순 고정 글자 수 분할이 아니라 문서 구조를 우선한다.

```text
제목
→ 장
→ 절
→ 조항
→ 항목
→ 문단
→ 긴 문단만 길이 기준 분할
```

초기 권장값:

```text
목표: 700~1,200 한국어 문자
최대: 약 1,500
최소: 약 250
Overlap: 100~200
```

Metadata 예시:

```json
{
  "source_type": "",
  "title": "",
  "meeting_name": "",
  "meeting_date": "",
  "category": "",
  "agenda": [],
  "section": "",
  "source_url": "",
  "original_filename": ""
}
```

---

## 17. OpenRouter Embedding 원칙

- 문서 Embedding과 Query Embedding은 동일 모델 사용
- `OPENROUTER_EMBEDDING_MODEL` 환경변수 관리
- 동일 문서 반복 Embedding 금지
- Batch Embedding 우선
- 결과 DB 캐싱
- `embedding_model` 저장
- 모델 변경 시 전체 Vector 재생성

---

## 18. Agent 발언 생성 구조

```text
SYSTEM RULE
+
AGENT PERSONA
+
SCENARIO CONTEXT
+
NEGOTIATION STATE
+
RAG EVIDENCE
+
SESSION MEMORY
+
OPPONENT LAST MESSAGE
        ↓
OpenRouter Chat API
        ↓
Structured Agent Response
```

가능하면 JSON 응답을 사용한다.

```json
{
  "speech": "",
  "intent": "counter_proposal",
  "proposed_terms": [],
  "concessions": [],
  "new_issues": [],
  "referenced_evidence_ids": []
}
```

---

## 19. Simulation Engine

```text
Simulation Engine
├─ Scenario Manager
├─ Turn Manager
├─ Speaker Selector
├─ Meeting Phase Manager
├─ Negotiation State Manager
├─ Agent Prompt Builder
├─ OpenRouter Client
├─ RAG Retriever
├─ Session Memory
├─ Evidence Manager
└─ End Condition Evaluator
```

CrewAI/AG2 등의 전체 Framework에 종속시키지 않고 FastAPI 내부에서 직접 구현한다.

---

## 20. 회담 Phase

```text
OPENING
AGENDA
PROPOSAL
RESPONSE
ISSUE_IDENTIFICATION
NEGOTIATION
COMPROMISE
FINALIZATION
AGREEMENT
PARTIAL_AGREEMENT
BREAKDOWN
```

Frontend:

```text
개회
→ 의제 확인
→ 제안
→ 의견 조율
→ 핵심 쟁점
→ 협상
→ 절충
→ 결과
```

---

## 21. Turn 운영

기본 6~8 Turn.

예:

```text
1 남측 수석대표
2 북측 단장
3 남측 실무대표
4 북측 실무대표
5 남측 수석대표
6 북측 단장
7 필요 시 추가 협상
8 최종화
```

진행 Agent는 매 Turn 호출하지 않고 필요한 시점에만 사용한다.

평가 Agent는 회담 종료 후 1회 호출한다.

---

## 22. Negotiation State

```json
{
  "current_round": 1,
  "current_phase": "PROPOSAL",
  "active_speaker": "",
  "issues": [],
  "proposals": [],
  "counter_proposals": [],
  "concessions": [],
  "agreements": [],
  "unresolved_issues": [],
  "tension_level": 0,
  "agreement_level": 0,
  "used_evidence": []
}
```

`tension_level`, `agreement_level`은 현실 예측값이 아니라 시뮬레이션 내부 상태값이다.

---

## 23. 회담 종료 조건

### 합의
핵심 쟁점 해결 + 양측 최종안 수용

### 부분합의
일부 합의 + 주요 이견 일부 잔존

### 결렬
핵심 Red Line 충돌 + 추가 협상 의미 없음

최종 상태:

```text
AGREEMENT
PARTIAL_AGREEMENT
BREAKDOWN
```

---

## 24. Session Memory

1차 PoC는 현재 회담 Session만 기억한다.

저장:
- 이전 발언
- 제안
- 수정안
- 양보
- 합의
- 미합의 쟁점
- 사용 Evidence

토큰 절감을 위해:

```text
최근 2~3 Turn
+
Session Summary
```

구조를 사용한다.

---

## 25. UI/UX 핵심 방향

이번 프로젝트는 **기능과 동일한 수준으로 UI/UX 완성도를 중요하게 본다.**

목표:

> **게임처럼 과하지 않으면서도 몰입감이 있고, 공공정책 서비스처럼 신뢰감 있으면서도 현대적인 시뮬레이션 UI**

---

## 26. 디자인 컨셉

**2.5D 아이소메트릭 또는 반입체 일러스트 기반 회담장 + 정책 대시보드**

전통적인 픽셀게임풍은 사용하지 않는다.

AI Town에서는 다음만 참고한다.

- Agent 상태 표현
- 캐릭터 배치
- 대화 시각화
- Simulation 감성

가져오지 않을 것:
- 자유 이동
- 마을 탐색
- NPC 스케줄
- 대규모 Agent Society

---

## 27. 캐릭터 스타일

- 평면적인 2D 아이콘 지양
- 정장 기반
- 실제 인물 얼굴 재현 금지
- 가상 인물
- 2.5D/반입체 표현
- 부드러운 그림자
- 깊이감
- 과도한 카툰/픽셀 느낌 지양

컬러:
- 남측: Muted Blue / Navy
- 북측: Muted Red / Burgundy
- 중립: Warm Gray / Beige / Brown / Deep Navy

---

## 28. 회담장 화면

```text
┌───────────────────────────────────────────────┐
│ AI 기반 남북 모의회담                         │
├────────────────────────────┬──────────────────┤
│                            │ 현재 핵심 쟁점   │
│ 남측 3명        북측 3명   │                  │
│                            │ 합의 상태        │
│        회담 테이블          │                  │
│                            │ 근거자료         │
│ 현재 발언자 Highlight      │                  │
│ 말풍선                     │                  │
├────────────────────────────┴──────────────────┤
│ Phase : 협상                  Round : 4 / 8    │
└───────────────────────────────────────────────┘
```

---

## 29. Agent UI 상태

```text
idle
thinking
speaking
waiting
```

발언자:
- 밝게 Highlight
- Glow 또는 조명
- 말풍선 표시

대기자:
- Tone Down

사용자가 항상 즉시 알아야 하는 정보:

1. 지금 누가 말하는가
2. 어떤 의제인가
3. 현재 Phase
4. 핵심 쟁점
5. 합의 진행 상태
6. 발언 근거

---

## 30. 근거자료 UI

발언 아래에 Evidence 1~3개만 간단히 표시한다.

```text
김도현 수석대표

"공동조사를 우선 실시하고
단계적으로 협력을 확대할 것을 제안합니다."

[AI 생성 가상 발언]

근거자료
📄 ○○ 남북합의서
📄 ○○ 실무회담 결과
```

상세 보기:
- 문서명
- 일자
- 자료 유형
- 관련 Chunk
- 원문 URL

---

## 31. 시작 화면

```text
AI 기반 남북 모의회담

의제
○ 이산가족 상봉 재개
○ 철도·도로 및 물류 협력
○ 군사적 긴장완화

모드
● AI vs AI
○ 내가 남측 대표

관계 상황
○ 개선
● 보통
○ 긴장

[회담 시작]
```

---

## 32. 결과 화면

```text
회담 결과
부분합의

핵심 합의사항
남측 주요 입장
북측 주요 입장
미합의 쟁점
주요 양보사항
후속 협상 필요사항
사용된 근거자료
```

---

## 33. 기술 스택

### Frontend
- React
- Vite
- TypeScript
- Vercel Free

### Backend
- Python
- FastAPI
- Pydantic
- httpx
- Render Free

### Database
- Supabase Free
- PostgreSQL
- pgvector

### AI/RAG
- OpenRouter Chat API
- OpenRouter Embeddings API

---

## 34. 무료 운영 원칙

```text
Vercel Free
Render Free
Supabase Free
OpenRouter 무료/무료범위 모델
```

유료 인프라는 기본 전제로 하지 않는다.

---

## 35. HTML 단일 파일 여부

단일 HTML 방식은 사용하지 않는다.

이유:
- 체감속도의 주요 병목은 React가 아니라 OpenRouter 응답, RAG 검색, Render Cold Start, 네트워크 왕복
- 이번 UI는 Agent 상태, Streaming, 2.5D 회담장, 분석 패널, 사용자 참여, Simulation State가 필요
- 따라서 React/Vite가 유지보수와 UI/UX 측면에서 더 적합

---

## 36. 성능 최적화

### 한 Turn = Backend 요청 1회

```text
Frontend
↓
POST /simulations/{id}/next
↓
FastAPI 내부
├─ RAG
├─ Prompt
├─ OpenRouter
├─ State Update
└─ Evidence Save
↓
Frontend
```

### OpenRouter Streaming
응답 전체를 기다리지 않고 생성되는 텍스트를 즉시 표시한다.

### Agent 호출 최소화
- 현재 발언 Agent만 호출
- 진행 Agent는 필요 시
- 평가 Agent는 종료 후

### 개발 모드
```text
DEV MODE: 4 Turn
DEMO MODE: 6~8 Turn
```

### Render Free Cold Start
- 시작 화면 진입 시 `/health` 백그라운드 호출
- 발표 전 `/health`, `/health/db`, `/health/openrouter` 점검

---

## 37. 전체 시스템 아키텍처

```text
┌──────────────────────────────────┐
│ Vercel Free                      │
│ React + Vite                     │
│ 2.5D Meeting UI                  │
└───────────────┬──────────────────┘
                │
                ▼
┌──────────────────────────────────┐
│ Render Free / FastAPI            │
│ Simulation Engine                │
│ RAG / Agent / State / Evidence   │
└──────────┬─────────────┬─────────┘
           │             │
           ▼             ▼
┌────────────────┐  ┌──────────────────┐
│ OpenRouter     │  │ Supabase Free    │
│ Chat API       │  │ PostgreSQL       │
│ Embeddings API │  │ pgvector         │
└────────────────┘  └──────────────────┘
```

---

## 38. Supabase 주요 테이블

```text
meetings
agreements
meeting_documents
document_chunks
historical_events

agents
agent_personas

scenarios
simulation_sessions
simulation_turns
simulation_evidence
simulation_results
```

### document_chunks
```text
id
document_id
chunk_index
content
source_type
title
meeting_name
meeting_date
category
agenda
section
source_url
original_filename
metadata
embedding_model
embedding
created_at
```

### agents
```text
id
name
side
role
persona
goal
negotiation_style
priorities
red_lines
acceptable_concessions
is_visible
is_llm_agent
created_at
```

---

## 39. API 기본 설계

```text
GET  /health
GET  /health/db
GET  /health/openrouter

GET  /api/v1/scenarios

POST /api/v1/simulations
GET  /api/v1/simulations/{id}

POST /api/v1/simulations/{id}/next
POST /api/v1/simulations/{id}/user-turn

GET  /api/v1/simulations/{id}/state
GET  /api/v1/simulations/{id}/evidence
GET  /api/v1/simulations/{id}/result

POST /api/v1/rag/search
```

---

## 40. 환경변수

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

OPENROUTER_API_KEY=
OPENROUTER_CHAT_MODEL=
OPENROUTER_EMBEDDING_MODEL=

DATA_GO_KR_API_KEY=

WEB_BASE_URL=http://localhost:5173
API_BASE_URL=http://localhost:8000
```

Secret은 Git에 commit하지 않는다.

---

## 41. 데이터 처리 순서

```text
1. 원본 데이터 확보
2. Raw 보관
3. 텍스트 추출
4. Metadata 보정
5. Chunking
6. Chunk 품질 검증
7. OpenRouter Embedding
8. Supabase pgvector 적재
9. RAG 검색 검증
10. Agent 연결
```

---

## 42. 2주 PoC 반드시 구현

### Data/RAG
- CSV 4종 정제
- 남북합의서 API 수집
- 해설자료 83건
- Chunking
- OpenRouter Embedding
- Supabase pgvector
- RAG 검색
- Evidence 표시

### Agent
- 남측 수석대표
- 남측 실무대표
- 북측 단장
- 북측 실무대표
- 진행 Agent
- 평가 Agent

### Simulation
- Scenario 3개
- AI vs AI
- 사용자 남측 대표
- 6~8 Turn
- Session Memory
- 합의 / 부분합의 / 결렬

### UI
- 2.5D 회담장
- 남측 3명 / 북측 3명
- 발언자 Highlight
- Thinking 상태
- 말풍선
- Round / Phase
- 쟁점 패널
- Evidence Panel
- 결과 화면

### Deployment
- Vercel Free
- Render Free
- Supabase Free

---

## 43. 1차 PoC 제외

```text
음성인식
TTS
실제 인물 음성복제
실제 인물 얼굴 재현
사용자 북측 대표
다중 사용자
장기 Memory
3D 게임엔진
대규모 Agent Society
자유 의제 무제한 입력
고급 PDF 자동보고서
```

---

## 44. 2주 개발 일정

### Day 1
- Repository 정리
- Frontend/Backend 환경
- Supabase/OpenRouter 연결

### Day 2~3
- CSV 정제
- 남북합의서 API 수집
- 해설자료 Metadata 보정

### Day 4
- Chunking
- 품질 검증

### Day 5
- OpenRouter Embedding
- Supabase pgvector
- RAG 검증

### Day 6~7
- 협상 Agent 4개
- Persona / Prompt

### Day 8
- 진행 Agent
- 평가 Agent

### Day 9
- Simulation Engine
- Turn / Phase / State / 종료조건

### Day 10~11
- 2.5D 회담 UI
- 6명 캐릭터
- 상태/말풍선/Evidence Panel

### Day 12
- 사용자 남측 대표 모드
- 추천 발언

### Day 13
- 결과 화면
- Streaming
- UX·속도 최적화

### Day 14
- 오류 대응
- 무료 배포 검증
- 시연 시나리오
- README / 발표 준비

---

## 45. 성공 기준

### Data/RAG
- 모든 원천데이터 출처 추적 가능
- 관련 합의서·해설자료 검색 가능
- 존재하지 않는 출처 생성 방지
- Source URL 확인 가능

### Agent
- 남측/북측 역할 차이 명확
- 수석/실무대표 역할 차이 명확
- 상대 발언 기억
- 근거 활용
- 과도한 반복 최소화

### Simulation
- Phase 진행
- Negotiation State 변화
- 합의/부분합의/결렬 도출

### UI/UX
- 처음 봐도 서비스 목적 이해 가능
- 현재 발언자 즉시 인식
- 1:1 챗봇처럼 보이지 않음
- 지나치게 2D/픽셀게임처럼 보이지 않음
- 공공정책 서비스 수준의 신뢰감
- 시연 시 시각적 임팩트 확보

### Performance
- Backend 요청 최소화
- Streaming
- Agent 순차 호출
- Render Cold Start 대응
- 불필요한 API 호출 최소화

---

## 46. 서비스 안내 문구

> 본 서비스는 공개된 남북회담 기록 및 공식자료를 기반으로 생성형 AI가 수행하는 가상 회담 시뮬레이션입니다. 등장인물은 가상의 인물이며 AI 생성 발언은 실제 정부 또는 실제 인물의 공식 입장을 의미하지 않습니다. 시뮬레이션 결과는 실제 남북협상 결과에 대한 예측이 아닙니다.

---

## 47. 최종 개발 방향

이번 PoC의 핵심 품질 기준은 네 가지다.

```text
1. 정확한 RAG 근거
2. 역할이 구분되는 Agent
3. 실제 협상처럼 변화하는 Simulation State
4. 세련된 2.5D UI/UX
```

최종적으로 구현하려는 것은 단순한 AI 대화 화면이 아니라,

> **근거, 역할, 기억, 목표, 협상상태, 시각적 몰입감을 가진 AI 기반 남북 모의회담 정책 시뮬레이션**

이다.
