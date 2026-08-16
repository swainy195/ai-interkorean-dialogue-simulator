# Phase 3 데이터 모델

## Mermaid ERD

```mermaid
erDiagram
    MEETINGS ||--o{ MEETING_DOCUMENTS : has
    AGREEMENTS ||--o{ MEETING_DOCUMENTS : related
    MEETINGS ||--o{ DOCUMENT_CHUNKS : source
    AGREEMENTS ||--o{ DOCUMENT_CHUNKS : source
    MEETING_DOCUMENTS ||--o{ DOCUMENT_CHUNKS : chunked

    MEETINGS {
        uuid id PK
        text source_meeting_id
        text meeting_name
        date start_date
        date end_date
        jsonb source_metadata
    }
    AGREEMENTS {
        uuid id PK
        text document_id UK
        text title
        date agreement_date
        text source_url
        jsonb source_metadata
    }
    MEETING_DOCUMENTS {
        uuid id PK
        text document_id UK
        uuid meeting_id FK
        uuid agreement_id FK
        text original_filename
        jsonb source_metadata
    }
    HISTORICAL_EVENTS {
        uuid id PK
        text event_id UK
        date event_date
        text title
        jsonb source_metadata
    }
    DOCUMENT_CHUNKS {
        uuid id PK
        text document_id
        uuid source_record_id
        int chunk_index
        vector embedding
        jsonb metadata
    }
```

## 관계 원칙

- 해설자료와 회담·합의서 관계는 확정된 경우에만 nullable FK를 설정한다.
- 제목 유사도만으로 `meeting_id` 또는 `agreement_id`를 자동 확정하지 않는다.
- `document_chunks.source_record_id`는 원본 테이블의 UUID를 가리키며, `source_table`로 실제 출처 테이블을 함께 기록한다.
- 임베딩 인덱스는 실제 chunk 규모와 검색 패턴을 확인한 뒤 별도 단계에서 추가한다.
