from __future__ import annotations

import re

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
    "도박",
    "불법",
    "마약",
    "대출",
    "도박",
}

NORMALIZE_RE = re.compile(r"[^0-9a-z가-힣]+", re.IGNORECASE)


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
        quality = "검색 의도와 수익화 가능성이 함께 높은 편입니다."
    elif score >= 80:
        quality = "정보성과 상업성이 균형 있게 섞여 있습니다."
    else:
        quality = "테스트용으로는 괜찮지만 우선순위는 조금 낮습니다."

    return (
        f"{candidate.source_topic} 축에서 확장된 키워드이며 "
        f"{candidate.content_format} 포맷과 잘 맞습니다. {quality}"
    )


def score_candidates(
    candidates: list[KeywordCandidate],
    minimum_score: int,
    limit: int,
    block_sensitive_topics: bool,
) -> list[RankedKeyword]:
    ranked: list[RankedKeyword] = []
    seen_keywords: set[str] = set()
    accepted_keywords: list[str] = []

    for candidate in candidates:
        normalized = _normalize(candidate.keyword)
        if normalized in seen_keywords:
            continue
        seen_keywords.add(normalized)

        if any(_keyword_similarity(normalized, existing) >= 0.72 for existing in accepted_keywords):
            continue

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
        accepted_keywords.append(normalized)

    ranked.sort(key=lambda item: (-item.score, item.keyword))
    return ranked[:limit]


def _normalize(value: str) -> str:
    normalized = NORMALIZE_RE.sub(" ", value.lower())
    return " ".join(normalized.split())


def _keyword_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0

    left_tokens = {token for token in left.split() if len(token) >= 2}
    right_tokens = {token for token in right.split() if len(token) >= 2}
    if not left_tokens or not right_tokens:
        return 0.0

    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    score = intersection / union if union else 0.0

    if left in right or right in left:
        score += 0.15
    return min(score, 1.0)
