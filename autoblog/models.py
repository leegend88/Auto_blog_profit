from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class KeywordCandidate:
    keyword: str
    source_topic: str
    intent: str
    content_format: str
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RankedKeyword:
    keyword: str
    source_topic: str
    intent: str
    content_format: str
    score: int
    why: str
    tags: tuple[str, ...]

    def as_dict(self, rank: int) -> dict[str, object]:
        return {
            "rank": rank,
            "keyword": self.keyword,
            "source_topic": self.source_topic,
            "intent": self.intent,
            "content_format": self.content_format,
            "score": self.score,
            "why": self.why,
            "tags": list(self.tags),
        }
