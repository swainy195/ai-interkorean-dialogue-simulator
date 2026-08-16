# Phase 4 데이터 적재

## 실행

```powershell
python scripts/ingest/run_phase4_ingestion.py
```

스크립트는 `.env`의 `SUPABASE_DB_URL`, `DATA_GO_KR_API_KEY`를 사용한다. 원본 CSV·HWP·PDF·Markdown은 수정하지 않는다.

## 출처와 정제

| 출처 | 입력 | 정제/적재 |
|---|---:|---:|
| 남북회담 정보·개최회담관리·연도별회담현황 CSV | 1,618행 | `meetings` 933행 |
| 이산가족 연표 CSV | 1,041행 | `historical_events` 1,041행 |
| 남북합의서 API | 응답 474 item, API partition total 480 | 중복 제거 후 `agreements` 79행 |
| 해설자료 Markdown | 83개 | `meeting_documents` 83행 |

남북합의서 API는 날짜만 포함한 광범위한 요청에서 0건을 반환했다. 공식 `thema` 값 1~6과 `country=북측`, `keyword=남북`을 partition으로 사용해 `19900101~20251231`을 조회했다. 응답은 12페이지였으며 `data/raw/agreements/api/`에 JSON 원문을 그대로 저장했다. 각 partition은 API `totalCount=80`을 보고했지만 실제 payload는 79개였고, `numOfRows=10` pagination도 70개에서 종료되어 API 자체의 count/page 불일치가 확인됐다. 누락 item은 추측하거나 생성하지 않았다.

정제 API 결과는 `data/processed/agreements/agreements.jsonl`과 `agreement_manifest.csv`에 저장하고, 전체 결과는 `data/processed/manifests/`에 기록한다.

## ID와 upsert

- meetings: `meeting:` + 안정적인 회담명·시작일·종료일 SHA-256
- agreements: `agreement:` + 제목·합의일·URL·파일명 SHA-256
- meeting_documents: `commentary:` + Manifest item 번호
- historical_events: 년대·날짜·내용 SHA-256

모든 적재는 PostgreSQL batch `executemany`와 `ON CONFLICT DO UPDATE`를 사용한다. 동일 스크립트를 재실행해도 row count가 증가하지 않는다.

해설자료의 `meeting_id`, `agreement_id`는 제목만으로 확정하지 않아 불확실한 관계를 연결하지 않았다. 원본 Manifest와 extraction Manifest는 `source_metadata`에 보존했다.

## 품질 결과

- agreements title null: 0
- agreements content empty: 0
- agreements source URL missing: 0
- agreement commentary title null: 0
- agreement commentary content empty: 0
- agreement commentary source URL missing: 0
- historical event date null: 0
- 중복 document/event ID: 0
- meetings 통합 경고: 251건. 연도별 현황 중 exact name 매칭이 불확실한 원본을 강제 병합하지 않고 provenance row로 보존했다.
- 해설자료 warning: 13건. 기존 extraction warning을 보존했다.
- `document_chunks`: 0건. Chunking·Embedding은 수행하지 않았다.

## Migration

Migration을 원격 PostgreSQL에 적용했고, `vector`, `pgcrypto`, 5개 테이블, `document_chunks.embedding = vector(2048)`를 실제 DB에서 검증했다. 재실행을 위해 `meetings.source_meeting_id` unique index도 추가했다.

## Phase 4.1 API 무결성 최종 검증

2026-08-16에 `keyword`와 `country`를 사용하지 않고 `19900101~20251231`, `numOfRows=100`, `pageNo=1`부터 검증했다. 날짜만 조회한 전체 요청과 `thema=1`, `thema=2` 요청은 모두 HTTP 200/resultCode 0이었지만 `totalCount=0`, payload 0을 반환했다. 따라서 이 조건만으로는 API 전체 범위를 재현할 수 없었다.

참고로 기존 수집 시 사용한 동작 조건(`keyword=남북`, `country=북측`, `thema=1~6`)에서는 thema=1과 thema=2가 각각 `totalCount=80`, payload 79, document_id unique 79, title+agreement_date unique 79, 완전 동일 중복 0을 반환했다. 두 응답 모두 실제 item의 `thema` 값이 1~5로 섞여 있어 thema 필터가 실제로 적용되지 않거나 서버 측 결함일 가능성이 있다. 각 요청은 page 1의 79건 뒤 page 2의 0건으로 종료되어 `totalCount=80`과 실제 payload 사이의 off-by-one 불일치도 재확인됐다.

80번째 record는 추측·생성하지 않았으며, 현재 `agreements` 79건은 변경하지 않았다. 이 결과는 데이터 소스 경고로 보존하고, API 재수집은 별도 검토 사항으로 남긴다.
