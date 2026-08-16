# Phase 8 UI/UX

## 목표

공개 자료 기반의 가상 남북 모의회담을 정책 서비스 수준의 화면으로 표현한다. 실제 인물이나 정부 입장을 재현하지 않으며, 공식 근거자료·시뮬레이션 가정·AI 생성 발언을 화면에서 구분한다.

## 회담 화면

- 따뜻한 회색·베이지 배경, 남측 muted navy/blue, 북측 burgundy/red를 사용한다.
- 회담장은 CSS 기반의 반입체/2.5D 공간으로 구성한다. 중앙 테이블과 부드러운 그림자로 깊이감을 표현한다.
- 남측 수석대표·실무대표·배석대표와 북측 단장·실무대표·배석대표 총 6명을 표시한다.
- 배석대표는 시각적 존재만 가지며 별도 LLM 호출을 하지 않는다.
- 현재 발언자는 강조하고, 대기자는 톤을 낮춘다. AI 호출 중에는 `thinking`, 발언 표시 중에는 `speaking` 상태를 보여준다.
- 발언은 말풍선으로 표시하고 `[E1]` 같은 Evidence ID를 함께 노출한다.

## 사용자 참여와 스트리밍

- `AI_VS_AI`와 `USER_SOUTH_VS_AI_NORTH`를 동일한 회담 화면에서 선택한다.
- 사용자 모드에서는 남측 대표 입력창과 추천 발언을 제공하고, 입력은 `/user-turn`으로 전송한다.
- AI 모드의 `/next/stream`은 SSE로 상태·토큰 조각·근거·완료 이벤트를 전달한다.
- 현재 서버는 OpenRouter에서 완성된 응답을 받은 뒤 안전한 길이로 나누어 SSE로 전송한다. upstream provider token streaming은 다음 성능 단계의 개선 대상이다.
- 스트림 오류 시 기존 `/next` 비스트리밍 API를 사용할 수 있도록 API 계층에 fallback 경로를 유지한다.

## 분석 패널과 결과

오른쪽 분석 패널에는 현재 의제, 진행 단계, 긴장 상태, 합의 사항, 미합의 쟁점, 공식 근거자료를 표시한다. 회담 종료 시 `AGREEMENT`, `PARTIAL_AGREEMENT`, `BREAKDOWN`을 각각 결과 카드로 보여줄 수 있다.

## 검증 결과

- 브라우저 AI vs AI smoke: 회담 생성, thinking/speaking 상태, AI 발언, Evidence 3건 표시 확인
- 브라우저 User vs AI smoke: 사용자 발언 입력, 북측 AI 응답, Evidence 3건 표시 확인
- API smoke: AI vs AI SSE의 `agent_state`·`token`·`done` 이벤트 및 User vs AI 200 응답 확인

## Phase 9 polish

- 긴 발언은 기본 4줄로 접고 `전체 발언 보기`로 확장한다.
- Evidence는 턴당 최대 3건만 노출하며 제목·출처 유형·날짜·관련도를 함께 표시한다. raw UUID는 화면에 표시하지 않는다.
- agreement level 숫자는 숨기고 진행 meter와 정책 언어로 표현한다.
- 첫 화면은 의제·모드·관계 상황·시작 동작만 제공하고 backend health 상태를 별도로 표시한다.
- 회담 중에는 진행/발언 버튼을 비활성화하고, 오류는 사용자용 안내 문구로만 표시한다.
- 새로고침 시 `session_id`만 localStorage에서 복구한다. 대화 내용과 secret은 저장하지 않는다.
- 1280/1440/1920px 데스크톱 레이아웃에서 회담장과 분석 패널을 유지하고 작은 화면에서는 아래로 재배치한다.

## 제한사항

실제 사용자 얼굴·음성·TTS·실시간 음성 입력은 포함하지 않는다. 운영 배포, 모바일 세부 최적화, provider 수준의 진짜 token streaming은 Phase 9 이후 범위다.
