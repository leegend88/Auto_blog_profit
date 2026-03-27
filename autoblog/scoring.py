from __future__ import annotations

from autoblog.models import KeywordCandidate, RankedKeyword


COMMERCIAL_HINTS = {
    "추천": 12,
    "비교": 14,
    "사용법": 8,
    "자동화": 12,
    "workflow": 10,
    "무료": 6,
    "유료": 6,
    "업무": 10,
    "생산성": 10,
    "tool": 8,
}

INFORMATIONAL_HINTS = {
    "사용법": 12,
    "정리": 10,
    "가이드": 10,
    "예시": 8,
    "방법": 8,
    "비교": 10,
    "추천": 8,
}

SENSITIVE_HINTS = {
    "성인",
    "우회",
    "크랙",
    "불법",
    "도박",
    "해킹",
    "돈 버는 법",
}


def _base_score(candidate: KeywordCandidate) -> int:
    score = 45

    for hint, value in COMMERCIAL_HINTS.items():
        if hint.lower() in candidate.keyword.lower():
            score += value

    for hint, value in INFORMATIONAL_HINTS.items():
        if hint.lower() in candidate.keyword.lower():
            score += value

    if candidate.intent == "commercial":
        score += 10
    elif candidate.intent == "mixed":
        score += 6
    else:
        score += 3

    if candidate.content_format in {"comparison", "tool-list"}:
        score += 8
    elif candidate.content_format == "tutorial":
        score += 6

    if "ai" in candidate.source_topic.lower():
        score += 6

    return min(score, 100)


def _is_sensitive(candidate: KeywordCandidate) -> bool:
    lowered = candidate.keyword.lower()
    return any(hint in lowered for hint in SENSITIVE_HINTS)


def _build_reason(candidate: KeywordCandidate, score: int) -> str:
    if score >= 90:
        quality = "검색 의도와 수익화 가능성이 모두 높습니다."
    elif score >= 80:
        quality = "정보성과 상업성이 균형 잡혀 있습니다."
    else:
        quality = "테스트용으로는 적합하지만 우선순위는 다소 낮습니다."

    return (
        f"{candidate.source_topic} 축에서 확장된 키워드이며 "
        f"{candidate.content_format} 포맷에 잘 맞습니다. {quality}"
    )


def score_candidates(
    candidates: list[KeywordCandidate],
    minimum_score: int,
    limit: int,
    block_sensitive_topics: bool,
) -> list[RankedKeyword]:
    ranked: list[RankedKeyword] = []
    seen_keywords: set[str] = set()

    for candidate in candidates:
        normalized = candidate.keyword.strip().lower()
        if normalized in seen_keywords:
            continue
        seen_keywords.add(normalized)

        if block_sensitive_topics and _is_sensitive(candidate):
            continue

        score = _base_score(candidate)
        if score < minimum_score:
            continue

        ranked.append(
            RankedKeyword(
                keyword=candidate.keyword,
                source_topic=candidate.source_topic,
                intent=candidate.intent,
                content_format=candidate.content_format,
                score=score,
                why=_build_reason(candidate, score),
                tags=candidate.tags,
            )
        )

    ranked.sort(key=lambda item: (-item.score, item.keyword))
    return ranked[:limit]
