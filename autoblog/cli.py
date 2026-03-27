from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from autoblog.config import AppConfig, load_config
from autoblog.content.generator import generate_post_for_keyword
from autoblog.dedupe import evaluate_duplicate_risk
from autoblog.logging_utils import append_jsonl_log
from autoblog.pipeline import KeywordPipeline
from autoblog.publishers.blogger import BloggerPublisher, BloggerPublisherError, build_draft_payload
from autoblog.quality import evaluate_post_quality


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate ranked AI/productivity blog keyword candidates."
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to the env file. Defaults to .env in the project root.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Override the number of ranked keywords to print.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print results as JSON instead of a formatted table.",
    )
    parser.add_argument(
        "--draft-keyword",
        default=None,
        help="Build a Blogger draft payload for the given keyword.",
    )
    parser.add_argument(
        "--generate-keyword",
        default=None,
        help="Generate article content for the given keyword.",
    )
    parser.add_argument(
        "--debug-generation",
        action="store_true",
        help="Print the fallback reason when OpenAI generation does not succeed.",
    )
    parser.add_argument(
        "--upload-draft-keyword",
        default=None,
        help="Upload a draft post to Blogger for the given keyword.",
    )
    parser.add_argument(
        "--upload-top-draft",
        action="store_true",
        help="Upload the top-ranked keyword as a Blogger draft.",
    )
    parser.add_argument(
        "--publish-keyword",
        default=None,
        help="Publish the given keyword to Blogger immediately after creating the post.",
    )
    parser.add_argument(
        "--publish-top",
        action="store_true",
        help="Publish the top-ranked keyword to Blogger immediately.",
    )
    parser.add_argument(
        "--list-blogs",
        action="store_true",
        help="List Blogger blogs available to the authenticated account.",
    )
    parser.add_argument(
        "--skip-quality-check",
        action="store_true",
        help="Upload even if the generated content does not pass quality checks.",
    )
    parser.add_argument(
        "--skip-duplicate-check",
        action="store_true",
        help="Upload even if a duplicate or highly similar title is detected.",
    )
    parser.add_argument(
        "--schedule-at",
        default=None,
        help="Schedule publish time in local blog timezone, e.g. 2026-03-26T09:00.",
    )
    return parser


def print_table(config: AppConfig, ranked_keywords: list[dict[str, object]]) -> None:
    print(f"Project: {config.project_name}")
    print(f"Niche: {config.primary_niche}")
    print(f"Schedule: {config.publish_schedule}")
    print()
    print("Top keyword candidates")
    print("-" * 80)

    for item in ranked_keywords:
        print(
            f"{item['rank']:>2}. {item['keyword']} | score={item['score']} | "
            f"intent={item['intent']} | format={item['content_format']}"
        )
        print(f"    why: {item['why']}")
        print(f"    tags: {', '.join(item['tags'])}")


def parse_schedule_at(raw: str, timezone_name: str) -> datetime:
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
    return parsed


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    env_path = Path(args.env_file)
    config = load_config(env_path)
    pipeline = KeywordPipeline(config)
    ranked_keywords = pipeline.run(limit=args.limit)
    log_path = Path(config.run_log_path)

    if args.list_blogs:
        try:
            blogs = BloggerPublisher(config).list_blogs()
        except BloggerPublisherError as exc:
            print(f"List blogs failed: {exc}")
            return 1
        print(json.dumps(blogs, ensure_ascii=False, indent=2))
        return 0

    if args.draft_keyword:
        post = generate_post_for_keyword(config, args.draft_keyword)
        quality = evaluate_post_quality(post)
        payload = build_draft_payload(
            title=post.title,
            content_html=post.content_html,
            labels=list(post.labels),
        )
        print(
            json.dumps(
                {
                    "title": payload.title,
                    "content_html": payload.content_html,
                    "labels": list(payload.labels),
                    "is_draft": payload.is_draft,
                    "generation_mode": post.generation_mode,
                    "quality": quality.as_dict(),
                    "debug_reason": post.debug_reason if args.debug_generation else "",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.generate_keyword:
        post = generate_post_for_keyword(config, args.generate_keyword)
        data = post.as_dict()
        data["quality"] = evaluate_post_quality(post).as_dict()
        if not args.debug_generation:
            data.pop("debug_reason", None)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    if args.upload_draft_keyword or args.upload_top_draft or args.publish_keyword or args.publish_top:
        keyword = args.upload_draft_keyword or args.publish_keyword
        if not keyword:
            if not ranked_keywords:
                print("No ranked keywords available to upload.")
                return 1
            keyword = str(ranked_keywords[0]["keyword"])

        post = generate_post_for_keyword(config, keyword)
        quality = evaluate_post_quality(post)
        recent_titles: list[str] = []
        duplicate_error = ""
        try:
            recent_titles = BloggerPublisher(config).list_recent_post_titles(
                max_results=config.recent_post_check_limit
            )
        except BloggerPublisherError as exc:
            duplicate_error = str(exc)
        duplicate = evaluate_duplicate_risk(post.title, log_path, recent_titles)
        payload = build_draft_payload(
            title=post.title,
            content_html=post.content_html,
            labels=list(post.labels),
        )

        if not args.skip_quality_check and (
            not quality.passed or quality.score < config.quality_min_score
        ):
            append_jsonl_log(
                log_path,
                {
                    "event": "quality_blocked",
                    "keyword": keyword,
                    "title": post.title,
                    "generation_mode": post.generation_mode,
                    "quality": quality.as_dict(),
                    "debug_reason": post.debug_reason,
                },
            )
            print(
                json.dumps(
                    {
                        "blocked": True,
                        "reason": "quality_check_failed",
                        "title": post.title,
                        "generation_mode": post.generation_mode,
                        "quality": quality.as_dict(),
                        "debug_reason": post.debug_reason if args.debug_generation else "",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1

        if not args.skip_duplicate_check and duplicate.blocked:
            append_jsonl_log(
                log_path,
                {
                    "event": "duplicate_blocked",
                    "keyword": keyword,
                    "title": post.title,
                    "generation_mode": post.generation_mode,
                    "quality": quality.as_dict(),
                    "duplicate": duplicate.as_dict(),
                    "duplicate_error": duplicate_error,
                    "debug_reason": post.debug_reason,
                },
            )
            print(
                json.dumps(
                    {
                        "blocked": True,
                        "reason": "duplicate_check_failed",
                        "title": post.title,
                        "generation_mode": post.generation_mode,
                        "quality": quality.as_dict(),
                        "duplicate": duplicate.as_dict(),
                        "duplicate_error": duplicate_error,
                        "debug_reason": post.debug_reason if args.debug_generation else "",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1

        try:
            publisher = BloggerPublisher(config)
            draft_result = publisher.publish_draft(payload)

            if args.schedule_at:
                scheduled_for = parse_schedule_at(args.schedule_at, config.blog_timezone)
                result = publisher.publish_post(
                    draft_result.post_id,
                    publish_date=scheduled_for,
                )
                event_name = "schedule_succeeded"
            elif args.publish_keyword or args.publish_top:
                result = publisher.publish_post(draft_result.post_id)
                scheduled_for = None
                event_name = "publish_succeeded"
            else:
                result = draft_result
                scheduled_for = None
                event_name = "upload_succeeded"
        except BloggerPublisherError as exc:
            append_jsonl_log(
                log_path,
                {
                    "event": "upload_failed",
                    "keyword": keyword,
                    "title": post.title,
                    "generation_mode": post.generation_mode,
                    "quality": quality.as_dict(),
                    "duplicate": duplicate.as_dict(),
                    "error": str(exc),
                },
            )
            print(f"Upload failed: {exc}")
            return 1

        append_jsonl_log(
            log_path,
            {
                "event": event_name,
                "keyword": keyword,
                "title": result.title,
                "post_id": result.post_id,
                "url": result.url,
                "status": result.status,
                "published": result.published,
                "scheduled_for": scheduled_for.isoformat() if args.schedule_at else "",
                "generation_mode": post.generation_mode,
                "quality": quality.as_dict(),
                "duplicate": duplicate.as_dict(),
                "duplicate_error": duplicate_error,
                "debug_reason": post.debug_reason,
            },
        )

        print(
            json.dumps(
                {
                    "post_id": result.post_id,
                    "title": result.title,
                    "url": result.url,
                    "status": result.status,
                    "published": result.published,
                    "scheduled_for": scheduled_for.isoformat() if args.schedule_at else "",
                    "generation_mode": post.generation_mode,
                    "quality": quality.as_dict(),
                    "duplicate": duplicate.as_dict(),
                    "duplicate_error": duplicate_error,
                    "debug_reason": post.debug_reason if args.debug_generation else "",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.json:
        print(json.dumps(ranked_keywords, ensure_ascii=False, indent=2))
    else:
        print_table(config, ranked_keywords)
    return 0
