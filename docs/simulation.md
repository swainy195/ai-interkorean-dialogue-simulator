# Phase 7 Simulation Engine

## Simulation Architecture

Phase 7는 협상 Agent 4개와 deterministic Moderator, 종료 시 1회 호출되는 Evaluator를 결합한다.

```text
POST /simulations/{id}/next
→ load state/memory
→ deterministic speaker selection
→ code-built RAG query
→ embedding + pgvector top 10
→ evidence diversity filter
→ current negotiation Agent 1회
→ StateUpdater
→ DB turn/evidence/session save
→ terminal이면 Evaluator 1회 + result save
```

Frontend의 1 request가 정확히 1 turn을 진행하며, 전체 자동 회담은 검증 스크립트에서만 반복한다.

## State Model

State에는 `current_round`, `current_phase`, active speaker, proposals, counter proposals, concessions, agreements, unresolved issues, used evidence IDs, tension/agreement 내부 상태값, summary, status가 포함된다. tension/agreement level은 현실 확률이나 정책 예측이 아닌 Simulation 내부 휴리스틱이다.

## Turn and Phase Flow

초기 speaker 순서는 `south_chief → north_chief → south_working → north_working`이다. 이후에는 intent와 round parity를 이용한다.

Phase 순서는 초기 8턴 기준 `OPENING → AGENDA → PROPOSAL → RESPONSE → NEGOTIATION → COMPROMISE → FINALIZATION`으로 제한한다. 상태 종료는 `AGREEMENT`, `PARTIAL_AGREEMENT`, `BREAKDOWN`이다.

## Moderator

Moderator는 실제 회담 발언자가 아니다. 매 턴 LLM을 호출하지 않고 현재 state를 검사하여 다음 phase, 쟁점, 반복 여부, 종료 후보를 deterministic하게 산출한다. 따라서 smoke test의 Moderator LLM calls는 0이다.

## Evaluator

Evaluator는 종료 시 1회 호출된다. 실제 북한의 수용 가능성이나 미래 성공 확률은 평가하지 않는다. 종료 state, 최근 핵심 turn, evidence 요약만 입력한다. 모델 JSON이 schema에 맞지 않을 때 이미 저장된 회담을 잃지 않도록 state 기반 fallback 결과를 저장한다.

## Memory

전체 raw prompt history를 매번 보내지 않는다. 최근 최대 3개 turn 요약, deterministic conversation summary, negotiation state, 현재 unresolved issues/proposals/concessions를 context로 전달한다. RAG query도 별도 LLM 없이 코드로 구성한다.

## End Conditions

- `AGREEMENT`: agreement level이 높고 미해결 쟁점이 없음
- `PARTIAL_AGREEMENT`: 일부 양보/합의 후보가 있으나 쟁점이 남음
- `BREAKDOWN`: 높은 tension/red-line 충돌 또는 max round에서 진전 부족

실제 3개 smoke는 모두 `BREAKDOWN`으로 종료됐다. 이는 당시 모델 응답과 내부 휴리스틱의 결과이며 현실 협상 전망이 아니다.

## DB Persistence

Migration `supabase/migrations/20260816_003_simulation_engine.sql`이 다음 테이블을 추가한다.

- `simulation_sessions`
- `simulation_turns`
- `simulation_evidence`
- `simulation_results`

Evidence는 화면용 `E1` ID와 별도로 실제 `document_chunks.id` UUID를 저장한다. 동일 turn의 동일 chunk는 unique 제약으로 중복 저장하지 않는다.

## API

- `POST /api/v1/simulations`: AI_VS_AI session 생성
- `POST /api/v1/simulations/{id}/next`: 정확히 한 turn 진행
- `GET /api/v1/simulations/{id}`: 현재 session/state
- `GET /api/v1/simulations/{id}/state`: state
- `GET /api/v1/simulations/{id}/evidence`: 누적 evidence
- `GET /api/v1/simulations/{id}/result`: 종료 평가

종료 session의 `/next`는 HTTP 422로 차단된다.

## Test Results

실제 smoke:

| scenario | rounds | result | evidence | evaluator |
|---|---:|---|---:|---|
| separated_families | 6 | BREAKDOWN | 30 | 저장 완료 |
| transport_cooperation | 4 | BREAKDOWN | 20 | 저장 완료 |
| military_tension | 4 | BREAKDOWN | 20 | 저장 완료 |

완료된 3개 session의 turn 순서, phase 전환, speaker role, evidence 누적, terminal 차단을 확인했다. 별도 디버깅 중 생성된 실패 시도 2개는 삭제하지 않고 보존했으며 terminal 상태로 정리했다.

## Cost Optimization

실제 완료 smoke의 Agent 호출은 14회, Evaluator 호출은 3회다. Moderator는 deterministic이라 LLM 호출 0회다. turn별 context는 최근 memory와 state만 사용한다. 실제 완료 smoke 기준 총 token/cost는 scenario별 로그와 OpenRouter usage를 통해 기록했다.

## Known Limitations

- 현재 smoke 결과가 모두 BREAKDOWN이며, agreement/partial 경로는 단위 휴리스틱 테스트로만 검증했다.
- Evaluator malformed JSON에 대한 fallback이 일부 실행될 수 있다.
- 사용자 참여 모드, SSE streaming, 2.5D UI, 실제 운영용 동시성 제어는 다음 Phase 범위다.

## Phase 7.1 Quality Tuning

기존 전 회담 BREAKDOWN 원인은 red-line/conflict를 매 턴 즉시 agreement level에 크게 감점하고, unresolved issue가 남으면 max round에서 BREAKDOWN으로 보내던 휴리스틱이었다. 또한 제안 간 의미 중복을 agreement candidate로 관리하지 않았고 Moderator는 호출되지 않았다.

변경 사항:

- proposed/counter-proposed terms의 2개 이상 token overlap을 candidate agreement로 추적
- concession/compromise/counter proposal에서 겹치는 조건을 agreement로 승격
- 단일 red-line은 unresolved로만 기록하고 반복되는 critical conflict만 breakdown에 반영
- max round에서 agreement/candidate/concession과 critical conflict를 함께 평가하여 PARTIAL_AGREEMENT 허용
- Evidence를 5개에서 기본 3개로 줄이고 content를 750자로 제한
- Prompt state를 최근 2 turn, 최근 proposal/counterproposal, active issues, current agreements/unresolved 중심으로 축약
- Moderator는 round 4 이후 조건부로 session당 최대 2회 호출
- Evaluator 필수 출력 필드를 단순화하고 schema fallback 유지
- 비표준 intent `conditional_acceptance` 등은 의미 보존 alias로 정규화

### Round-level Replay

최종 smoke의 state replay 결과:

- separated_families: agreement level 47→100, tension 0, candidate 12, unresolved 0 → `AGREEMENT`
- transport_cooperation: agreement level 47→100, tension 0→17, candidate 16, critical red line 1, unresolved 3 → `BREAKDOWN`
- military_tension: agreement level 47→100, tension 0→5, candidate 14, unresolved 6, critical red line 0 → `PARTIAL_AGREEMENT`

### Phase 7.1 Smoke

| scenario | rounds | result | evidence/turn | moderator | evaluator fallback |
|---|---:|---|---:|---:|---:|
| separated_families | 6 | AGREEMENT | 3 | 2 | 0 |
| transport_cooperation | 6 | BREAKDOWN | 3 | 2 | 0 |
| military_tension | 6 | PARTIAL_AGREEMENT | 3 | 2 | 0 |

전체 18 Agent calls, Moderator 6 calls, Evaluator 3 calls을 수행했다. 전체 73,670 tokens, cost 0.00945915이며 prompt token 평균은 3,425/turn으로 Phase 7의 약 5,323보다 감소했다. 이 결과는 현실의 협상 전망이 아닌 Simulation branch 동작 검증이다.

## Phase 9 Runtime Notes

- AI vs AI의 한 턴은 `/next/stream` 하나로 처리하며 state, turn, evidence, terminal result를 완료 이벤트에 포함한다.
- User vs AI의 사용자 발언과 북측 응답은 `/user-turn` 하나로 처리한다.
- 진행 중 버튼은 비활성화되어 중복 turn 요청을 막는다.
- provider-level streaming은 Structured JSON과 Evidence ID 검증의 안정성을 위해 보류하고, 검증된 speech를 SSE로 전달한다.
