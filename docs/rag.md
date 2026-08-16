# Phase 5 RAG 구축

## Architecture

Phase 5는 `source table → deterministic chunk → OpenRouter Embedding → Supabase pgvector` 흐름으로 구현했다. Chat 모델은 사용하지 않았고, Agent·Simulation Engine·UI는 구현하지 않았다.

## Chunking Strategy

- `agreements` 79개: 제목·분야·합의일자·국가·지역·시설 metadata prefix와 본문을 결합하고 문단/문장 경계 우선으로 약 1,200자 단위 분할
- `meeting_documents` 83개: 해설 Markdown 본문을 heading/문단 경계 중심으로 분할
- `meetings` 933개: 짧은 metadata row를 1 record=1 chunk로 유지
- `historical_events` 1,041개: 1 event=1 chunk
- chunk ID는 `{document_id}:chunk:{index}` 의미를 갖는 `(document_id, chunk_index)` 유니크 키로 관리
- 원본 provenance는 `metadata`와 `original_filename`에 유지하며 검색 content에는 손상된 provenance 파일명을 포함하지 않음

## Chunk Results

| source_type | documents | chunks | avg chars | short warning (<250) |
|---|---:|---:|---:|---:|
| agreement | 79 | 175 | 833.01 | 31 |
| agreement_commentary | 83 | 319 | 1,019.28 | 15 |
| meeting | 933 | 933 | 102.98 | 929 |
| historical_event | 1,041 | 1,041 | 115.52 | 1,019 |
| **total** | **2,136** | **2,468** | - | **1,994** |

빈 chunk 0, 1,500자 초과 0, 완전 동일 chunk 0, `(document_id, chunk_index)` 중복 0, replacement character 0이다. 짧은 meeting/event chunk는 1 record=1 chunk 설계에 따른 warning이다. source URL 누락은 1,974건이며 원천 CSV의 URL 부재를 보존했다.

결과 파일:

- `data/processed/chunks/agreements/chunks.jsonl`
- `data/processed/chunks/meeting_documents/chunks.jsonl`
- `data/processed/chunks/meetings/chunks.jsonl`
- `data/processed/chunks/historical_events/chunks.jsonl`
- `data/processed/chunks/all_chunks.jsonl`
- `data/processed/chunks/chunk_manifest.csv`

## Embedding

- Endpoint: OpenRouter `/api/v1/embeddings`
- Model: `nvidia/nemotron-3-embed-1b:free`
- Dimension: 2048
- content hash와 model이 같은 chunk는 cache를 재사용
- 최종 2,468개 vector 생성, 실패 0
- 최초 2,471개 생성 후 chunk content 정정으로 stale 3개를 제거하고 최종 2,468개로 정합화
- 최종 보완 실행: cache 재사용 2,289개, 신규 179개, API request 12회
- API 응답 usage 합계는 실행별로 기록되며 무료 모델이라 cost 필드는 반환되지 않음

## Supabase Schema and Load

Migration `supabase/migrations/20260816_002_rag_search.sql`에 exact cosine search 함수 `match_document_chunks`를 추가했다. PoC 규모이므로 approximate vector index는 추가하지 않았다.

실제 DB 결과:

- `document_chunks`: 2,468
- embedding null: 0
- agreement: 175
- agreement_commentary: 319
- meeting: 933
- historical_event: 1,041

적재는 `(document_id, chunk_index)` 기준 batch upsert이며 재실행 시 중복을 만들지 않는다. chunk 재생성으로 남은 stale 3건도 제거했다.

## Retrieval Flow

`test_rag_retrieval.py`가 한국어 질의를 Embedding한 뒤 `match_document_chunks(query_embedding, 10, source_types, theme_filter)`를 호출한다. similarity는 `1 - (embedding <=> query_embedding)`이다.

검색 함수 출력은 id, document_id, content, title, source_type, source_url, metadata, similarity를 포함한다. 향후 Agent 연결 시 Top 10에서 동일 document 최대 2개 제한 및 Top 3~5 context 축소를 적용할 수 있다.

## Korean Retrieval Smoke Test

Top 1 결과:

1. 이산가족 상봉: `제 15차 장관급회담 공동보도문 해설자료`, agreement commentary, similarity 0.484275
2. 철도·도로: `제1차 남북총리회담 합의서 해설자료`, agreement commentary, similarity 0.530938
3. 군사 긴장완화: `남북고위급회담 설명자료`, agreement commentary, similarity 0.607827
4. 고위급 회담: `남북고위급회담 설명자료`, agreement commentary, similarity 0.599804

수동적인 Top 5 1차 판정은 각각 3/5, 5/5, 5/5, 5/5 관련으로 Precision@5 약 0.90이다. 이는 작은 smoke test이며 정식 평가셋이 아니다.

## Known Limitations

- HWP 추출 결과의 표/페이지 구조가 일부 평탄화되어 있다.
- 일부 해설자료에는 OCR이 아닌 추출 artifact와 짧은 chunk가 남아 있다.
- meetings와 historical_events의 짧은 chunk 및 URL 누락은 원천 데이터 특성이다.
- API source의 79건 known range issue는 Phase 4 provenance로 유지한다.
- similarity threshold는 아직 강제하지 않았고, 검색 결과 분포를 기반으로 후속 조정한다.
