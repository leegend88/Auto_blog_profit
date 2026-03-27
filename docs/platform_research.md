# Platform Research

작성일: 2026-03-24

## 현재 결론

현재 프로젝트의 1차 플랫폼은 **Google Blogger**로 진행합니다.

이유:

- 비용 없이 시작 가능
- AdSense 연동이 공식 지원됨
- 수익화 테스트를 빠르게 시작하기 좋음

다만 장기적으로 자동화 확장성과 운영 자유도는 자체 호스팅 WordPress가 더 높기 때문에,
**Blogger에서 수익 검증 후 WordPress 전환 검토** 전략이 가장 현실적입니다.

## 공식 자료 요약

### 1. Blogger

- Google/Blogger 공식 도움말에 따르면 Blogger에서는 AdSense 연결이 가능함
- Auto ads 사용도 가능함
- 무료에 가깝고 시작 속도가 빠름

공식 자료:

- https://support.google.com/blogger/answer/1269077?hl=en
- https://support.google.com/adsense/answer/9155509?hl=en

### 2. WordPress.com

- WordPress.com 공식 지원 문서에 따르면 WordAds 사용에는 Premium 이상 플랜과 기본 도메인 조건이 필요함
- 다른 광고 프로그램과 병행 가능하다고 안내함

공식 자료:

- https://wordpress.com/support/wordads-and-earn/
- https://wordpress.com/pricing/

### 3. WordPress.org

- WordPress.org는 소프트웨어 자체는 무료이지만 호스팅과 도메인은 별도 준비가 필요함

공식 자료:

- https://wordpress.org/download/

## 실무 판단

아래는 공식 문서를 바탕으로 한 **추론**입니다.

- 비용을 쓰지 않고 테스트를 시작하려면 Blogger가 가장 적합함
- 수익화 자체만 놓고 보면 Blogger가 불리한 플랫폼은 아님
- 다만 자동화, SEO, 구조 제어, 확장성은 WordPress 쪽이 더 유리함
- 따라서 현재 단계에서는 Blogger가 맞고, 이후 성과가 확인되면 WordPress 이전이 합리적임

## 추천 운영 순서

1. Blogger로 블로그 개설
2. 소수의 품질 글로 테스트
3. AdSense 연결 및 승인 시도
4. 수익과 트래픽 확인
5. 필요 시 WordPress 이전 검토
