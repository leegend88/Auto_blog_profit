# GitHub Actions Setup

## 목표

로컬 PC가 꺼져 있어도 GitHub Actions에서 자동으로 글 생성과 Blogger 업로드를 실행합니다.

## 포함된 워크플로

- 파일: `.github/workflows/auto-blog.yml`
- 지원 방식:
  - 수동 실행 `workflow_dispatch`
  - 매일 자동 실행 `schedule`

현재 스케줄은 아래 cron으로 설정되어 있습니다.

```text
0 0 * * *
```

GitHub Actions의 cron은 **UTC 기준**입니다.
즉 `0 0 * * *`는 한국 시간 기준 `매일 오전 9시`입니다.

## GitHub Secrets 등록

레포지토리 `Settings > Secrets and variables > Actions > New repository secret` 에 아래 값을 등록합니다.

필수:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `BLOGGER_BLOG_ID`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`

권장:

- `ENABLE_SECOND_PASS_REWRITE`
- `OPENAI_TIMEOUT_SECONDS`
- `QUALITY_MIN_SCORE`
- `RECENT_POST_CHECK_LIMIT`
- `ENABLE_HUMAN_REVIEW`
- `BLOCK_SENSITIVE_TOPICS`

선택:

- `ENABLE_COUPANG_PARTNERS`
- `COUPANG_PARTNERS_ID`

## 첫 테스트 권장 순서

1. GitHub에 프로젝트 업로드
2. Secrets 등록
3. `Actions` 탭으로 이동
4. `Auto Blog Profit` 워크플로 선택
5. `Run workflow`
6. `action=generate` 로 먼저 테스트
7. 결과가 정상이면 `action=upload_draft_keyword`
8. 마지막으로 schedule 자동 실행 확인

## 추천 테스트 입력값

- `action`: `generate`
- `keyword`: `AI 자동화 툴 추천`
- `debug_generation`: `true`

그 다음:

- `action`: `upload_draft_keyword`
- `keyword`: `AI 자동화 툴 추천`

## 예약 발행 테스트

수동 실행에서 아래처럼 입력할 수 있습니다.

- `action`: `upload_draft_keyword`
- `keyword`: `AI 자동화 툴 추천`
- `schedule_at`: `2026-03-27T09:00`

이 시간은 `.env`와 동일하게 `Asia/Seoul` 기준으로 처리됩니다.

## 로그 확인

워크플로 실행 후 `Artifacts`에서 `auto-blog-logs`를 다운로드하면 `logs/runs.jsonl`을 확인할 수 있습니다.

## 주의사항

- GitHub Actions의 cron은 몇 분 정도 지연될 수 있습니다.
- Blogger/Google OAuth 토큰이 만료되면 업로드가 실패할 수 있습니다.
- 중복 검사와 품질 검수에 걸리면 업로드는 차단되고 로그에 남습니다.
# GitHub Pages for Images

이미지 URL을 실제로 노출하려면 GitHub 저장소에서 `Pages`를 켜야 합니다.

1. `Settings`
2. `Pages`
3. `Build and deployment`를 `GitHub Actions`로 선택

이후 `Auto Blog Profit` 워크플로가 실행되면 `public/generated-images/` 아래의 SVG 파일이 Pages로 배포됩니다.

이미지 기본 URL 형식:

```text
https://<github-username>.github.io/<repo-name>/generated-images/
```

워크플로에서는 이 경로를 `PUBLIC_IMAGE_BASE_URL`로 자동 설정합니다.
