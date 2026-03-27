from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    project_name: str
    blog_platform: str
    blog_timezone: str
    publish_schedule: str
    primary_niche: str
    target_language: str
    target_country: str
    keyword_seed_topics: list[str]
    keyword_fetch_limit: int
    keyword_score_min: int
    openai_api_key: str
    openai_model: str
    enable_second_pass_rewrite: bool
    openai_timeout_seconds: int
    quality_min_score: int
    run_log_path: str
    recent_post_check_limit: int
    enable_inline_images: bool
    max_section_cards: int
    image_output_dir: str
    public_image_base_url: str
    blogger_blog_id: str
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    enable_human_review: bool
    max_posts_per_day: int
    block_sensitive_topics: bool


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _load_env_file(env_path: Path) -> None:
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def load_config(env_path: Path) -> AppConfig:
    if env_path.exists():
        _load_env_file(env_path)

    return AppConfig(
        project_name=os.getenv("PROJECT_NAME", "Auto_blog_profit"),
        blog_platform=os.getenv("BLOG_PLATFORM", "blogger"),
        blog_timezone=os.getenv("BLOG_TIMEZONE", "Asia/Seoul"),
        publish_schedule=os.getenv("PUBLISH_SCHEDULE", "09:00"),
        primary_niche=os.getenv("PRIMARY_NICHE", "ai_productivity_tools"),
        target_language=os.getenv("TARGET_LANGUAGE", "ko"),
        target_country=os.getenv("TARGET_COUNTRY", "KR"),
        keyword_seed_topics=_get_list(
            "KEYWORD_SEED_TOPICS",
            "chatgpt,gemini,ai productivity,ai workflow,ai tools",
        ),
        keyword_fetch_limit=int(os.getenv("KEYWORD_FETCH_LIMIT", "20")),
        keyword_score_min=int(os.getenv("KEYWORD_SCORE_MIN", "70")),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", ""),
        enable_second_pass_rewrite=_get_bool("ENABLE_SECOND_PASS_REWRITE", True),
        openai_timeout_seconds=int(os.getenv("OPENAI_TIMEOUT_SECONDS", "120")),
        quality_min_score=int(os.getenv("QUALITY_MIN_SCORE", "70")),
        run_log_path=os.getenv("RUN_LOG_PATH", "logs/runs.jsonl"),
        recent_post_check_limit=int(os.getenv("RECENT_POST_CHECK_LIMIT", "20")),
        enable_inline_images=_get_bool("ENABLE_INLINE_IMAGES", True),
        max_section_cards=int(os.getenv("MAX_SECTION_CARDS", "3")),
        image_output_dir=os.getenv("IMAGE_OUTPUT_DIR", "public/generated-images"),
        public_image_base_url=os.getenv("PUBLIC_IMAGE_BASE_URL", "").rstrip("/"),
        blogger_blog_id=os.getenv("BLOGGER_BLOG_ID", ""),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        google_refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN", ""),
        enable_human_review=_get_bool("ENABLE_HUMAN_REVIEW", True),
        max_posts_per_day=int(os.getenv("MAX_POSTS_PER_DAY", "1")),
        block_sensitive_topics=_get_bool("BLOCK_SENSITIVE_TOPICS", True),
    )
