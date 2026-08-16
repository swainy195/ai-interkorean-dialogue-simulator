# Phase 3 데이터 구조 분석

## 분석 범위

- `data/raw/*.csv` 4종
- `data/raw/agreement_commentaries/download_manifest.csv`
- `data/processed/agreement_commentaries/extraction_manifest.csv`
- 처리된 Markdown 83개와 원본 첨부파일 83개

원본 파일은 수정하지 않았다. CSV는 모두 CP949로 읽혔고, Manifest는 UTF-8 BOM 형식이었다.

## CSV 구조

| 원본 | 행 | 열 | 컬럼 |
|---|---:|---:|---|
| 통일부_남북회담 정보_20181231.csv | 667 | 10 | 연도, 회담분야, 회담명, 개최회담, 개최국가, 개최지역, 개최시설, 회담시작일자, 회담종료일자, 회담일수 |
| 통일부_남북관계관리단_연도별회담현황데이터관리_20240920.csv | 271 | 3 | 연도별회담내용, 연도별회담제목, 작성일 |
| 통일부_남북관계관리단_개최회담관리_20240920.csv | 680 | 5 | 개최회담명, 개최회담수, 개최방문수, 회담시작일, 회담종료일 |
| 통일부_남북이산가족 연표_20211216.csv | 1,041 | 3 | 년대, 날짜, 내용 |

모든 CSV에서 공백 기준 null은 0건이고, 완전 중복 행도 0건이었다. 날짜 컬럼은 ISO 형식 `YYYY-MM-DD`였다.

### 고유키 후보와 주의점

| 원본 | 고유 후보 | 판단 |
|---|---|---|
| 남북회담 정보 | 개최회담 | 파일 안에서는 유일하지만 다른 원본과 공유되는 안정적인 ID는 아니다. 해시 기반 source key를 사용한다. |
| 개최회담관리 | 개최회담명 | 파일 안에서는 유일하지만 동일 회담명 변형·다른 연도 가능성이 있다. 자연 FK로 사용하지 않는다. |
| 연도별회담현황 | 없음 | 제목과 내용이 반복될 수 있어 `hash(source_file, row, values)`를 사용한다. |
| 이산가족 연표 | 없음 | 년대·날짜·내용 조합 해시를 사용한다. |

### 샘플 3건

#### 통일부_남북회담 정보

1. `2018 / 정치 / 남북고위급회담 / 제1차 남북고위급회담 / 중립 / 판문점 남측 / 평화의집 / 2018-01-09`
2. `2018 / 정치 / 남북고위급회담 / 제3차 남북고위급회담 / 중립 / 판문점 남측 / 평화의집 / 2018-06-01`
3. `2018 / 정치 / 남북고위급회담 / 제4차 남북고위급회담 / 중립 / 판문점 북측 / 통일각 / 2018-08-13`

#### 연도별회담현황데이터관리

1. `남북적십자 파견원 접촉 (5회, 중감위회의실)`
2. `남북적십자 예비회담 (13회, 중감위회의실)`
3. `남북적십자 예비회담 (12회, 중감위회의실)`

이 데이터는 회담 일정을 설명하는 서술형 내용이므로 `meetings`의 원문 메타데이터 또는 별도 source metadata로 보존한다.

#### 개최회담관리

1. `남북적십자 파견원 제1차 접촉 / 1회 / 1방문 / 1971-08-20`
2. `남북적십자 제1차 예비회담 / 1회 / 1방문 / 1971-09-20`
3. `남북적십자 의제문안 제1차 실무회의 / 1회 / 1방문 / 1972-02-21`

#### 남북이산가족 연표

1. `1950년대 / 1954-02-08 / 실향사민 북한송환 희망자 등록`
2. `1950년대 / 1954-02-27 / 북한실향사민 24명 판문점 통해 북으로 송환`
3. `1950년대 / 1955-03-21 / 한적, 국제적십자위원회의 이산가족문제 해결 위한 중재 제의 수락`

## Manifest 및 해설자료

`download_manifest.csv`는 84개 게시물, 11개 컬럼이다. 첨부파일 83건은 `already_exists` 또는 성공 상태로 확보되어 있다. `extraction_manifest.csv`는 83건, 13개 컬럼이며 원본 파일 82 HWP와 1 PDF에 대응하는 Markdown 83개가 있다.

해설자료와 합의서·회담의 제목은 유사하지만 제목만으로 확정 관계를 만들지 않는다. 따라서 `meeting_documents.meeting_id`, `meeting_documents.agreement_id`는 nullable로 두고, 확정된 매칭만 적재 단계에서 설정한다. 원본 item 번호, attachment ID, URL, 파일명, 추출 방식과 경고는 `source_metadata`에 보존한다.

## 남북합의서 API 매핑

공식 API 응답은 최상위 `resultCode`, `resultMsg`, `items`, `numOfRows`, `pageNo`, `totalCount`를 사용한다. 테스트 응답은 10건, `totalCount=18`이었다.

| API field | 내부 컬럼 |
|---|---|
| agmnt_ymd | agreement_date |
| bgng_ymd | meeting_start_date |
| end_ymd | meeting_end_date |
| catgory | category |
| cn | content |
| country | country |
| dwld_url | download_url |
| facility | facility |
| filenm | original_filename |
| region | region |
| sj | subject |
| thema | theme |
| title | title |
| url | source_url |

API 날짜 `YYYYMMDD`와 기존 CSV ISO 날짜는 모두 PostgreSQL `date`로 정규화한다. 원문 날짜 또는 파싱 실패 값은 `source_metadata`에 둔다.

## 통합 설계 이유

- `meetings`: 667건의 회담 기본정보를 중심으로 개최회담관리의 횟수·방문수와 연도별 현황 원문을 통합한다.
- `agreements`: API가 제공하는 합의서 메타데이터와 내용을 별도 보존한다.
- `meeting_documents`: 해설자료·기타 문서를 원본 파일 및 추출 provenance와 함께 보존한다.
- `historical_events`: 이산가족 연표를 사건 단위로 저장한다.
- `document_chunks`: 이후 RAG를 위해 모든 문서 유형을 수용하며 `vector(2048)`을 사용한다.

## ID 및 provenance

row 순번을 영구 ID로 사용하지 않는다. 적재 단계에서 안정적인 필드 조합의 SHA-256으로 `meeting:{hash}`, `agreement:{hash}`, `historical-event:{hash}` 등을 생성한다. 해설자료는 다운로드 Manifest의 `item_no`를 식별 보조값으로만 보존하고 `commentary:{item_no}`와 원본 파일명·URL을 함께 기록한다.

모든 핵심 테이블에는 `source_type`, `source_url` 또는 문서별 provenance, `source_metadata jsonb`를 둔다.
