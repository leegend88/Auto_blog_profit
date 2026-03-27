from __future__ import annotations

from dataclasses import dataclass

from autoblog.config import AppConfig
from autoblog.content.images import inject_inline_images
from autoblog.content.openai_client import OpenAIContentClient, OpenAIContentError
from autoblog.content.templates import build_draft_html, build_meta_description


@dataclass(frozen=True)
class GeneratedPost:
    title: str
    content_html: str
    meta_description: str
    labels: tuple[str, ...]
    generation_mode: str
    debug_reason: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "content_html": self.content_html,
            "meta_description": self.meta_description,
            "labels": list(self.labels),
            "generation_mode": self.generation_mode,
            "debug_reason": self.debug_reason,
        }


def generate_post_for_keyword(
    config: AppConfig, keyword: str, labels: list[str] | None = None
) -> GeneratedPost:
    default_labels = tuple(labels or ["AI", "Productivity", "Blogger"])
    meta_description = build_meta_description(keyword)

    if not config.openai_api_key:
        content_html = build_draft_html(keyword)
        if config.enable_inline_images:
            content_html = inject_inline_images(
                content_html,
                title=keyword,
                keyword=keyword,
                max_section_cards=config.max_section_cards,
                output_dir=config.image_output_dir,
                public_base_url=config.public_image_base_url,
            )
        return GeneratedPost(
            title=keyword,
            content_html=content_html,
            meta_description=meta_description,
            labels=default_labels,
            generation_mode="template_fallback",
            debug_reason="OPENAI_API_KEY is missing.",
        )

    client = OpenAIContentClient(config)
    try:
        response = client.generate_blog_post(keyword)
    except OpenAIContentError as exc:
        content_html = build_draft_html(keyword)
        if config.enable_inline_images:
            content_html = inject_inline_images(
                content_html,
                title=keyword,
                keyword=keyword,
                max_section_cards=config.max_section_cards,
                output_dir=config.image_output_dir,
                public_base_url=config.public_image_base_url,
            )
        return GeneratedPost(
            title=keyword,
            content_html=content_html,
            meta_description=meta_description,
            labels=default_labels,
            generation_mode="template_fallback",
            debug_reason=str(exc),
        )

    content_html = response.get("content_html", build_draft_html(keyword))
    title = response.get("title", keyword)
    if config.enable_inline_images:
        content_html = inject_inline_images(
            content_html,
            title=title,
            keyword=keyword,
            max_section_cards=config.max_section_cards,
            output_dir=config.image_output_dir,
            public_base_url=config.public_image_base_url,
        )

    return GeneratedPost(
        title=title,
        content_html=content_html,
        meta_description=response.get("meta_description", meta_description),
        labels=tuple(response.get("labels", list(default_labels))),
        generation_mode=(
            "openai_rewritten" if config.enable_second_pass_rewrite else "openai"
        ),
        debug_reason="",
    )
