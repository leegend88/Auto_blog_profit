from __future__ import annotations

from autoblog.models import KeywordCandidate


TOPIC_PATTERNS: dict[str, list[tuple[str, str, str, tuple[str, ...]]]] = {
    "chatgpt": [
        ("챗GPT 사용법", "informational", "tutorial", ("chatgpt", "guide")),
        ("챗GPT 업무 자동화", "commercial", "tutorial", ("chatgpt", "workflow")),
        ("챗GPT 프롬프트 예시", "informational", "template", ("chatgpt", "prompt")),
        ("챗GPT 유료 무료 차이", "mixed", "comparison", ("chatgpt", "pricing")),
        ("챗GPT 생산성 활용법", "commercial", "tutorial", ("chatgpt", "productivity")),
    ],
    "gemini": [
        ("제미나이 사용법", "informational", "tutorial", ("gemini", "guide")),
        ("제미나이와 챗GPT 비교", "commercial", "comparison", ("gemini", "chatgpt")),
        ("제미나이 업무 활용", "commercial", "tutorial", ("gemini", "workflow")),
        ("제미나이 무료 기능 정리", "informational", "listicle", ("gemini", "free")),
        ("제미나이 프롬프트 예시", "informational", "template", ("gemini", "prompt")),
    ],
    "ai productivity": [
        ("AI 생산성 도구 추천", "commercial", "tool-list", ("ai", "tools")),
        ("무료 AI 생산성 도구", "commercial", "tool-list", ("ai", "free")),
        ("AI 업무 효율화 방법", "informational", "tutorial", ("ai", "workflow")),
        ("AI 회의록 정리 도구 비교", "commercial", "comparison", ("ai", "meeting-notes")),
        ("AI 문서 요약 도구 추천", "commercial", "tool-list", ("ai", "summarization")),
    ],
    "ai workflow": [
        ("AI 자동화 툴 추천", "commercial", "tool-list", ("ai", "automation")),
        ("AI 업무 자동화 사례", "informational", "listicle", ("ai", "case-study")),
        ("노코드 AI 자동화 방법", "commercial", "tutorial", ("ai", "no-code")),
        ("AI 이메일 작성 자동화", "commercial", "tutorial", ("ai", "email")),
        ("AI 일정 관리 도구 비교", "commercial", "comparison", ("ai", "calendar")),
    ],
    "ai tools": [
        ("무료 AI 툴 추천", "commercial", "tool-list", ("ai", "free-tools")),
        ("유료 AI 툴 비교", "commercial", "comparison", ("ai", "paid-tools")),
        ("AI 번역 도구 비교", "commercial", "comparison", ("ai", "translation")),
        ("AI 글쓰기 도구 추천", "commercial", "tool-list", ("ai", "writing")),
        ("AI 이미지 생성 도구 비교", "mixed", "comparison", ("ai", "image-generation")),
    ],
}


FALLBACK_PATTERNS: list[tuple[str, str, str, tuple[str, ...]]] = [
    ("{topic} 사용법", "informational", "tutorial", ("guide",)),
    ("{topic} 추천", "commercial", "tool-list", ("recommendation",)),
    ("{topic} 비교", "commercial", "comparison", ("comparison",)),
    ("{topic} 업무 활용법", "commercial", "tutorial", ("workflow",)),
]


def expand_seed_topics(seed_topics: list[str]) -> list[KeywordCandidate]:
    candidates: list[KeywordCandidate] = []

    for topic in seed_topics:
        normalized = topic.strip().lower()
        topic_patterns = TOPIC_PATTERNS.get(normalized, FALLBACK_PATTERNS)

        for pattern in topic_patterns:
            keyword, intent, content_format, tags = pattern
            if "{topic}" in keyword:
                keyword = keyword.format(topic=topic)
            candidates.append(
                KeywordCandidate(
                    keyword=keyword,
                    source_topic=topic,
                    intent=intent,
                    content_format=content_format,
                    tags=tags,
                )
            )

    return candidates
