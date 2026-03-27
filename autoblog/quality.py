from __future__ import annotations

import re
from dataclasses import dataclass

from autoblog.content.generator import GeneratedPost


HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
SENTENCE_SPLIT_RE = re.compile(r"[.!?]\s+|[。！？]\s*")
LIST_ITEM_RE = re.compile(r"<li\b", re.IGNORECASE)
HEADING_RE = re.compile(r"<h[23]\b", re.IGNORECASE)
INLINE_IMAGE_RE = re.compile(r"<img\b", re.IGNORECASE)

BANNED_PHRASES = (
    "무조건",
    "반드시 써야",
    "완벽한",
    "압도적인",
    "인생을 바꾸는",
    "혁신적인",
)
AFFILIATE_HEAVY_PHRASES = (
    "지금 구매",
    "최저가",
    "구매 링크",
    "강력 추천",
    "쿠팡 파트너스",
)
PRACTICAL_EXAMPLE_HINTS = (
    "예를 들면",
    "예를 들어",
    "실제로는",
    "실무에서는",
    "회의록",
    "이메일",
    "번역",
    "요약",
    "일정 관리",
)
COMPARISON_HINTS = (
    "비교",
    "장단점",
    "선택 기준",
    "추천 대상",
    "언제",
    "적합",
)
FAQ_HINTS = ("faq", "자주 묻는 질문", "많이 묻는 질문")
HUMAN_SIGNAL_HINTS = (
    "다만",
    "반대로",
    "굳이",
    "보통은",
    "이 경우에는",
    "이런 날에는",
)
NON_RECOMMENDATION_HINTS = (
    "굳이 쓸 필요는",
    "맞지 않을 수",
    "오히려 번거로울",
    "필요 없을 수",
    "비추천",
)
AI_SLANG_PATTERNS = (
    "지금부터 알아보겠습니다",
    "정리해 보겠습니다",
    "도움이 됩니다",
    "살펴보겠습니다",
    "소개하겠습니다",
    "핵심 포인트를 확인해보세요",
)


@dataclass(frozen=True)
class QualityCheckResult:
    passed: bool
    score: int
    issues: tuple[str, ...]
    word_count: int
    paragraph_count: int
    heading_count: int
    list_item_count: int
    metrics: dict[str, int | bool]

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "score": self.score,
            "issues": list(self.issues),
            "word_count": self.word_count,
            "paragraph_count": self.paragraph_count,
            "heading_count": self.heading_count,
            "list_item_count": self.list_item_count,
            "metrics": self.metrics,
        }


def evaluate_post_quality(post: GeneratedPost) -> QualityCheckResult:
    issues: list[str] = []
    score = 100

    plain_text = _plain_text(post.content_html)
    word_count = len([token for token in plain_text.split(" ") if token.strip()])
    paragraph_count = post.content_html.count("<p>")
    heading_count = len(HEADING_RE.findall(post.content_html))
    list_item_count = len(LIST_ITEM_RE.findall(post.content_html))
    inline_image_count = len(INLINE_IMAGE_RE.findall(post.content_html))
    lowered = plain_text.lower()

    has_faq = any(hint in lowered for hint in FAQ_HINTS)
    practical_example_hits = sum(1 for hint in PRACTICAL_EXAMPLE_HINTS if hint in plain_text)
    comparison_hits = sum(1 for hint in COMPARISON_HINTS if hint in plain_text)
    affiliate_phrase_hits = sum(1 for phrase in AFFILIATE_HEAVY_PHRASES if phrase in plain_text)
    human_signal_hits = sum(1 for hint in HUMAN_SIGNAL_HINTS if hint in plain_text)
    non_recommendation_hits = sum(1 for hint in NON_RECOMMENDATION_HINTS if hint in plain_text)
    ai_slang_hits = sum(plain_text.count(pattern) for pattern in AI_SLANG_PATTERNS)
    heading_bonus = heading_count >= 4
    list_balance_bonus = 2 <= list_item_count <= 12
    sentence_count = len(
        [sentence for sentence in SENTENCE_SPLIT_RE.split(plain_text) if sentence.strip()]
    )
    avg_words_per_sentence = int(word_count / sentence_count) if sentence_count else 0

    if len(post.title.strip()) < 10:
        issues.append("title_too_short")
        score -= 10

    if word_count < 350:
        issues.append("content_too_short")
        score -= 35

    if paragraph_count < 6:
        issues.append("too_few_paragraphs")
        score -= 15

    if heading_count < 4:
        issues.append("too_few_headings")
        score -= 12

    for phrase in BANNED_PHRASES:
        if phrase in plain_text:
            issues.append(f"banned_phrase:{phrase}")
            score -= 8

    repeated_starts = _count_repeated_sentence_starts(plain_text)
    if repeated_starts >= 3:
        issues.append("repetitive_sentence_openings")
        score -= 15

    if "추후 llm 본문 생성 결과로 교체됩니다" in lowered:
        issues.append("template_placeholder_remaining")
        score -= 40

    if post.generation_mode == "template_fallback":
        issues.append("template_fallback_used")
        score -= 20

    if not has_faq:
        issues.append("faq_missing")
        score -= 10

    if practical_example_hits < 2:
        issues.append("practical_examples_missing")
        score -= 12

    if comparison_hits < 2:
        issues.append("weak_selection_criteria")
        score -= 10

    if affiliate_phrase_hits >= 3:
        issues.append("too_promotional")
        score -= 18

    if avg_words_per_sentence > 35:
        issues.append("sentences_too_dense")
        score -= 10

    if human_signal_hits < 2:
        issues.append("human_texture_missing")
        score -= 10

    if non_recommendation_hits < 1:
        issues.append("missing_non_recommendation_angle")
        score -= 8

    if ai_slang_hits >= 3:
        issues.append("ai_sounding_phrases")
        score -= 18

    if heading_bonus:
        score += 4

    if list_balance_bonus:
        score += 3

    if inline_image_count >= 2:
        score += 4

    score = max(min(score, 100), 0)
    fatal_issues = {
        "content_too_short",
        "template_placeholder_remaining",
        "too_promotional",
    }

    return QualityCheckResult(
        passed=score >= 72 and not any(issue in fatal_issues for issue in issues),
        score=score,
        issues=tuple(issues),
        word_count=word_count,
        paragraph_count=paragraph_count,
        heading_count=heading_count,
        list_item_count=list_item_count,
        metrics={
            "has_faq": has_faq,
            "practical_example_hits": practical_example_hits,
            "comparison_hits": comparison_hits,
            "affiliate_phrase_hits": affiliate_phrase_hits,
            "avg_words_per_sentence": avg_words_per_sentence,
            "heading_bonus": heading_bonus,
            "list_balance_bonus": list_balance_bonus,
            "inline_image_count": inline_image_count,
            "human_signal_hits": human_signal_hits,
            "non_recommendation_hits": non_recommendation_hits,
            "ai_slang_hits": ai_slang_hits,
        },
    )


def _plain_text(content_html: str) -> str:
    no_tags = HTML_TAG_RE.sub(" ", content_html)
    return WHITESPACE_RE.sub(" ", no_tags).strip()


def _count_repeated_sentence_starts(text: str) -> int:
    starts: dict[str, int] = {}
    for sentence in SENTENCE_SPLIT_RE.split(text):
        sentence = sentence.strip()
        if not sentence:
            continue
        start = " ".join(sentence.split()[:3]).lower()
        if not start:
            continue
        starts[start] = starts.get(start, 0) + 1
    return sum(1 for count in starts.values() if count >= 2)
