from __future__ import annotations

from autoblog.config import AppConfig
from autoblog.models import RankedKeyword
from autoblog.scoring import score_candidates
from autoblog.sources.seed_expander import expand_seed_topics


class KeywordPipeline:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def run(self, limit: int | None = None) -> list[dict[str, object]]:
        candidates = expand_seed_topics(self.config.keyword_seed_topics)
        ranked = score_candidates(
            candidates=candidates,
            minimum_score=self.config.keyword_score_min,
            limit=limit or self.config.keyword_fetch_limit,
            block_sensitive_topics=self.config.block_sensitive_topics,
        )
        return [item.as_dict(rank=index) for index, item in enumerate(ranked, start=1)]
