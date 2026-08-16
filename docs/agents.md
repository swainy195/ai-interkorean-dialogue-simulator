# Phase 6 협상 Agent

## Architecture

`POST /api/v1/agents/respond`는 한 요청에서 다음 흐름을 처리한다.

```text
request
→ scenario/persona validation
→ query embedding
→ match_document_chunks top 10
→ document diversity/evidence selection (최대 5)
→ persona prompt
→ OpenRouter Chat JSON response
→ Pydantic schema + Evidence ID validation
→ response
```

이번 Phase에는 4개 협상 Agent만 구현했다. 진행 Agent, 평가 Agent, Turn Manager, Simulation Engine, 사용자 참여 모드는 구현하지 않았다.

## Personas

| key | 가명 | 측 | 역할 | 성향 |
|---|---|---|---|---|
| south_chief | 김도현 | 남측 | 수석대표 | 원칙·방향·단계적 타협 |
| south_working | 박서진 | 남측 | 실무대표 | 일정·절차·검증·실행 |
| north_chief | 리명철 | 북측 | 단장 | 원칙·조건부 수용·역제안 |
| north_working | 최광혁 | 북측 | 실무대표 | 세부 조건·일정·수정 문구 |

가명은 실제 인물을 지칭하지 않는다. Agent는 실제 정부나 당국의 공식 입장을 대변하지 않으며 가상의 Simulation 조건 안에서만 발언한다.

## Scenarios

- `separated_families`: 이산가족 상봉 재개
- `transport_cooperation`: 남북 철도·도로 및 물류 협력
- `military_tension`: 군사적 긴장완화

Scenario 목표는 현실 예측값이 아니라 테스트용 가상 조건이다.

## Prompt Structure

Prompt는 다음 순서로 구성된다.

```text
SYSTEM RULES
AGENT PERSONA
SCENARIO CONTEXT
CURRENT NEGOTIATION CONTEXT
RAG EVIDENCE
OPPONENT LAST MESSAGE
OUTPUT FORMAT
```

역사적 사실과 AI가 제안하는 현재 Simulation 조건을 분리하도록 system rule에 명시했다. 발언은 JSON object이며 2~4개 문단, 약 300~700자 범위를 지향한다.

## RAG Evidence

현재 의제·상대 발언·협상 context를 Embedding하여 `match_document_chunks` top 10을 조회한다. 이후 같은 `document_id`는 최대 2개로 제한하고, `agreement` 또는 `agreement_commentary`를 우선하여 최종 최대 5개를 선택한다.

최종 Evidence에는 `E1`부터 순서대로 내부 ID를 부여한다. Agent의 `referenced_evidence_ids`는 제공된 ID 집합과 비교하며, 존재하지 않는 ID가 있으면 validation error로 처리한다.

## Structured Response

```json
{
  "speech": "...",
  "intent": "proposal",
  "proposed_terms": [],
  "concessions": [],
  "red_line_conflicts": [],
  "new_issues": [],
  "referenced_evidence_ids": ["E1"],
  "confidence_note": "..."
}
```

허용 intent는 `proposal`, `counter_proposal`, `clarification`, `concession`, `objection`, `compromise`, `closing`이다. Markdown code fence가 붙은 JSON은 안전하게 한 번 파싱 보정하며, 구조가 맞지 않으면 실패한다. 배열 안의 object는 문자열 항목으로 제한적으로 정규화한다.

## Live Test Results

실제 OpenRouter 호출 6회를 수행했다.

- 이산가족 상봉: 4개 Agent 각각 1회
- 철도·도로 협력: south_chief 1회
- 군사적 긴장완화: north_chief 1회
- 모든 호출 HTTP/응답 처리 성공
- 모든 응답 JSON schema 검증 성공
- invalid Evidence ID: 0
- 발언 길이: 488~725자
- 역할 차이: 수석대표는 proposal, 북측 Agent는 counter_proposal 경향; 실무대표는 절차·조건 중심

사용량:

- model: `google/gemma-3-27b-it`
- calls: 6
- prompt tokens: 24,545
- completion tokens: 2,989
- total tokens: 27,534
- reported cost: 0.00314422

## Tests

- Persona/Scenario load
- Prompt section ordering
- Structured response parsing
- invalid intent rejection
- Evidence ID selection and diversity
- `pytest`: 7 passed
- FastAPI endpoint smoke test: HTTP 200, evidence 5개
- Frontend `npm run build`: PASS

## Known Limitations

- 6회 smoke test는 정식 협상 품질 평가셋이 아니다.
- 역사적 사실 hallucination은 Evidence ID 검증으로 1차 제한했지만 사실성 전체를 자동 보증하지 않는다.
- 현재는 자동 턴 진행, 상태 변화, 합의도·긴장도, 평가 Agent가 없다.
- Chat 모델의 JSON 필드가 완전히 안정적이지 않아 제한적인 타입 정규화를 적용했다.
