from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


NON_WORD_RE = re.compile(r"[^0-9a-z가-힣]+", re.IGNORECASE)


@dataclass(frozen=True)
class DuplicateCheckResult:
    blocked: bool
    similarity_score: float
    matched_title: str
    source: str
    issues: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "blocked": self.blocked,
            "similarity_score": round(self.similarity_score, 3),
            "matched_title": self.matched_title,
            "source": self.source,
            "issues": list(self.issues),
        }


def evaluate_duplicate_risk(
    candidate_title: str,
    log_path: Path,
    existing_titles: list[str] | None = None,
) -> DuplicateCheckResult:
    candidate_normalized = _normalize(candidate_title)
    candidate_tokens = _tokenize(candidate_title)

    best_score = 0.0
    best_title = ""
    best_source = ""
    issues: list[str] = []

    for title in _read_logged_titles(log_path):
        score = _similarity(candidate_normalized, candidate_tokens, title)
        if score > best_score:
            best_score = score
            best_title = title
            best_source = "run_log"

    for title in existing_titles or []:
        score = _similarity(candidate_normalized, candidate_tokens, title)
        if score > best_score:
            best_score = score
            best_title = title
            best_source = "blogger_recent_posts"

    if best_score >= 0.95:
        issues.append("near_exact_title_match")
    elif best_score >= 0.8:
        issues.append("high_title_similarity")
    elif best_score >= 0.65:
        issues.append("moderate_title_similarity")

    return DuplicateCheckResult(
        blocked=best_score >= 0.8,
        similarity_score=best_score,
        matched_title=best_title,
        source=best_source,
        issues=tuple(issues),
    )


def _read_logged_titles(log_path: Path) -> list[str]:
    if not log_path.exists():
        return []

    titles: list[str] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("event") not in {"upload_succeeded", "publish_succeeded", "schedule_succeeded"}:
            continue
        title = entry.get("title")
        if isinstance(title, str) and title.strip():
            titles.append(title)
    return titles


def _normalize(value: str) -> str:
    normalized = NON_WORD_RE.sub(" ", value.lower())
    return " ".join(normalized.split())


def _tokenize(value: str) -> set[str]:
    return {token for token in _normalize(value).split() if len(token) >= 2}


def _similarity(candidate_normalized: str, candidate_tokens: set[str], title: str) -> float:
    title_normalized = _normalize(title)
    if not title_normalized:
        return 0.0

    if candidate_normalized == title_normalized:
        return 1.0

    title_tokens = _tokenize(title)
    if not candidate_tokens or not title_tokens:
        return 0.0

    intersection = len(candidate_tokens & title_tokens)
    union = len(candidate_tokens | title_tokens)
    jaccard = intersection / union if union else 0.0

    contains_bonus = 0.0
    if candidate_normalized in title_normalized or title_normalized in candidate_normalized:
        contains_bonus = 0.15

    return min(jaccard + contains_bonus, 1.0)
