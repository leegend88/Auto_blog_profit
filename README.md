# Auto Blog Profit

특정 주제의 키워드를 매일 선정하고, 작성부터 발행까지 자동화하며, 수익화 가능성을 테스트하는 블로그 자동화 프로젝트입니다.

## 현재 운영 전략

현재 1차 플랫폼은 **Google Blogger**로 진행합니다.
현재 1차 핵심 주제는 **AI/생산성 도구**입니다.

선정 이유:

- 초기 비용 없이 시작 가능
- Google 계정 기반으로 개설과 운영이 간단함
- AdSense 연동이 공식적으로 지원됨
- 수익화 검증 전 단계에서 가장 부담이 적음

전환 조건:

- Blogger에서 트래픽과 수익화가 정상적으로 확인되면
- 그다음 단계에서 **자체 호스팅 WordPress** 이전을 검토

## 수익화 방향

- 1차 수익화: Google AdSense
- 2차 수익화: 쿠팡 파트너스, 기타 제휴 마케팅, 디지털 상품, 이메일 구독 수집
- 운영 원칙: 자동화는 사용하되 저품질 대량 발행은 피하고, 초안 검수 흐름을 유지

추가 메모:

- 추후 제품 추천형 글에는 `쿠팡 파트너스` 링크를 삽입하는 방향을 고려
- 적용 우선 대상: AI 도구 사용 환경, 업무용 액세서리, 책상 셋업, 모니터암, 키보드, 마이크 등 주변기기형 콘텐츠

## 자동화 목표 범위

1. 매일 정해진 시간에 키워드 후보 수집
2. 필터링 규칙으로 키워드 선정
3. 검색 의도에 맞는 글 구조 생성
4. 제목, 본문, 메타 설명, 태그 초안 작성
5. Blogger 초안 저장 또는 예약 발행
6. 발행 로그와 성과 데이터 기록

## 확정된 주제

- 메인 니치: `AI/생산성 도구`
- 우선 타겟 독자: AI를 업무, 학습, 개인 생산성에 활용하려는 초급~중급 사용자
- 기본 콘텐츠 유형:
  - 사용법 가이드
  - 툴 비교
  - 업무 자동화 예시
  - 프롬프트 예시
  - 무료/유료 도구 추천

예시 키워드:

- `챗GPT 사용법`
- `제미나이 사용법`
- `AI 업무 자동화`
- `회의록 AI 정리`
- `무료 AI 툴 추천`
- `AI 번역 도구 비교`

## 권장 초기 아키텍처

- `scheduler`: 매일 실행 시간 관리
- `keyword_pipeline`: 키워드 수집, 점수화, 중복 제거
- `content_pipeline`: 제목, 목차, 본문, 요약 생성
- `publisher`: Blogger API 업로드
- `compliance_guard`: 정책 리스크, 중복 위험, 과장 표현 점검
- `analytics`: 게시물 성과 및 수익 지표 정리

## 현재 플랫폼 판단

- **지금 시작용**: Blogger
- **수익 검증 후 확장용**: WordPress.org

자세한 비교는 [platform_research.md](c:/Users/leej0/OneDrive/바탕%20화면/vibe-coding/Auto_blog_profit/docs/platform_research.md) 참고.

## 다음 구현 순서

1. Blogger 블로그 개설
2. AdSense 연결 가능 상태까지 기본 세팅
3. AI/생산성 키워드 수집 소스 확정
4. 글 생성 템플릿 설계
5. 썸네일 생성 방식 확정
6. Blogger 업로드 자동화 구현

## 발행 방식 추천

- 초기: 자동 생성 -> 초안 저장 -> 사람이 1회 검수 후 발행
- 안정화 이후: 검수 규칙 통과 시 예약 발행

이 방식이 수익화 테스트 단계에서 가장 안전합니다.

자동화 상세 흐름은 [automation_flow.md](c:/Users/leej0/OneDrive/바탕%20화면/vibe-coding/Auto_blog_profit/docs/automation_flow.md) 참고.
GitHub Actions 설정은 [github_actions_setup.md](c:/Users/leej0/OneDrive/바탕%20화면/vibe-coding/Auto_blog_profit/docs/github_actions_setup.md) 참고.

## 현재 구현 상태

- AI/생산성 시드 키워드 확장
- 키워드 점수화 및 상위 후보 선정
- OpenAI API 기반 키워드별 본문 생성
- OpenAI 2차 리라이트 패스로 문체 자연스러움 개선
- 품질 검수와 업로드 차단 규칙
- 중복/유사 제목 차단
- JSONL 실행 로그 저장
- GitHub Actions 자동 실행 워크플로
- SVG 기반 자동 이미지 삽입
- Blogger 발행용 초안 payload 및 실제 초안 업로드
- OpenAI 미설정 시 글 초안용 HTML 템플릿 fallback
- 추후 쿠팡 파트너스 링크 삽입을 고려한 수익화 확장 방향 반영

## 실행 방법

프로젝트 루트에서 아래처럼 실행할 수 있습니다.

```bash
python main.py --env-file .env.example
```

JSON 형식으로 보고 싶다면:

```bash
python main.py --env-file .env.example --json
```

선정된 키워드로 Blogger 초안 payload를 미리 만들려면:

```bash
python main.py --env-file .env.example --draft-keyword "AI 자동화 툴 추천"
```

실제 본문 생성 결과를 미리 보려면:

```bash
python main.py --env-file .env --generate-keyword "AI 자동화 툴 추천"
```

OpenAI 생성 실패 원인까지 같이 보려면:

```bash
python main.py --env-file .env --generate-keyword "AI 자동화 툴 추천" --debug-generation
```

실제 Blogger 초안으로 업로드하려면:

```bash
python main.py --env-file .env --upload-draft-keyword "AI 자동화 툴 추천"
```

또는 현재 점수 기준 1위 키워드를 바로 초안 업로드하려면:

```bash
python main.py --env-file .env --upload-top-draft
```

예약 발행으로 올리려면:

```bash
python main.py --env-file .env --upload-draft-keyword "AI 자동화 툴 추천" --schedule-at "2026-03-26T09:00"
```

## Blogger 초안 업로드 조건

`.env` 파일에 아래 값이 필요합니다.

- `BLOGGER_BLOG_ID`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`

현재 구현은 Blogger API 공식 문서의 `posts.insert`와 `isDraft=true` 방식에 맞춰 초안 저장을 수행합니다.
본문 생성은 OpenAI `Responses API`를 사용하며, API 키가 없거나 요청 실패 시 템플릿 초안으로 대체됩니다.
기본값으로 `ENABLE_SECOND_PASS_REWRITE=true`가 적용되어, 1차 생성 뒤 한 번 더 자연스럽게 다듬습니다.
응답이 느릴 때를 대비해 `OPENAI_TIMEOUT_SECONDS`로 대기 시간을 조절할 수 있습니다.
업로드 전에는 기본 품질 검수를 수행하고, 결과는 `RUN_LOG_PATH`의 JSONL 파일에 저장합니다.
업로드 전에는 최근 Blogger 글 제목과 실행 로그를 기준으로 중복/유사 제목 검사도 수행합니다.
`--schedule-at`을 사용하면 블로그 타임존 기준으로 초안을 예약 발행합니다.

## 품질 검수

기본 검수 항목:

- 본문 길이
- 문단 수
- 제목/헤딩 구조
- 과장 표현 포함 여부
- 반복적인 문장 시작
- FAQ 존재 여부
- 구체 예시 포함 여부
- 비교/선택 기준 포함 여부
- 광고성 문구 과다 여부
- 문장 밀도
- 템플릿 플레이스홀더 잔존 여부

## 자동 이미지

현재는 저작권 리스크를 줄이기 위해 `SVG data URI` 방식으로 본문에 직접 삽입합니다.

- 깔끔한 텍스트 썸네일
- 섹션 구분용 카드형 이미지
- 비교표 카드
- 체크리스트형 요약 카드

설정:

- `ENABLE_INLINE_IMAGES=true`
- `MAX_SECTION_CARDS=3`

품질 검사 무시 후 강제 업로드가 필요하면:

```bash
python main.py --env-file .env --upload-draft-keyword "AI 자동화 툴 추천" --skip-quality-check
```

중복 검사 무시 후 강제 업로드가 필요하면:

```bash
python main.py --env-file .env --upload-draft-keyword "AI 자동화 툴 추천" --skip-duplicate-check
```

내 계정의 Blogger 블로그 목록과 `BLOGGER_BLOG_ID`를 확인하려면:

```bash
python main.py --env-file .env --list-blogs
```
## Human-Like Writing Tuning

현재 프롬프트와 품질 검수는 아래 요소를 강제하거나 점수에 반영합니다.

- 과하게 반듯한 브로셔 문체 금지
- `다만`, `반대로`, `굳이` 같은 신중한 연결 포함
- `누구에게 맞는지 / 굳이 안 써도 되는 사람` 구간 포함
- 실무형 예시 최소 2개 이상 포함
- FAQ 3개 고정
- 반복적인 AI식 문장(`정리해 보겠습니다`, `도움이 됩니다`) 감점

즉, 목표는 “매끈한 AI 요약문”보다 “직접 정리한 실용 블로그 글”에 가깝게 만드는 것입니다.
