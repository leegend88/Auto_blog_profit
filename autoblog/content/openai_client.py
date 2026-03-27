from __future__ import annotations

import json
import socket
from urllib import request
from urllib.error import HTTPError, URLError

from autoblog.config import AppConfig
from autoblog.content.templates import build_draft_html, build_meta_description


class OpenAIContentError(RuntimeError):
    """Raised when OpenAI content generation fails."""


class OpenAIContentClient:
    RESPONSES_URL = "https://api.openai.com/v1/responses"
    DEFAULT_LABELS = ["AI", "Productivity", "Blogger"]
    BANNED_PHRASES = (
        "혁신적인",
        "완벽한",
        "획기적인",
        "무조건",
        "반드시 써야 하는",
        "압도적인",
        "인생을 바꾸는",
    )
    TITLE_PATTERNS = (
        "{keyword}, 막상 써보면 어디까지 편한지 정리",
        "{keyword} 추천 전에 먼저 볼 기준",
        "{keyword} 활용법: 이런 업무에는 잘 맞고 이런 경우엔 애매합니다",
    )

    def __init__(self, config: AppConfig, timeout_seconds: int | None = None) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds or config.openai_timeout_seconds

    def generate_blog_post(self, keyword: str) -> dict[str, object]:
        if not self.config.openai_api_key:
            raise OpenAIContentError("OPENAI_API_KEY is missing.")

        parsed = self._send_payload(self._build_generation_payload(keyword), "generation")
        post = self._extract_post_json(parsed, keyword)

        if self.config.enable_second_pass_rewrite:
            rewritten = self._send_payload(
                self._build_rewrite_payload(keyword, post),
                "rewrite",
            )
            post = self._extract_post_json(rewritten, keyword, fallback=post)

        return post

    def _build_generation_payload(self, keyword: str) -> dict[str, object]:
        model = self.config.openai_model or "gpt-5-mini"
        title_patterns = " / ".join(
            pattern.format(keyword=keyword) for pattern in self.TITLE_PATTERNS
        )
        instructions = (
            "You are generating a Korean Blogger post about AI and productivity tools. "
            "Return only valid json with keys title, meta_description, content_html, labels. "
            "The article must be useful, grounded, natural, and suitable for AdSense review. "
            "Do not include markdown fences. Use HTML in content_html with h2, h3, p, ul, li tags. "
            "Target Korean readers and write natural Korean that sounds like a practical blogger, not a brochure. "
            "Avoid medical, legal, or financial advice. Avoid unsupported promises and avoid made-up claims. "
            "Use specific situations, tradeoffs, limitations, and realistic caveats. "
            "Do not sound overly polished, overly symmetrical, or repetitive. "
            "Vary paragraph length naturally and keep some sentences plain rather than theatrical. "
            "The writing should feel like a careful person organizing thoughts after looking into the topic, "
            "not like a brand campaign or a generic AI summary."
        )
        user_prompt = (
            f"Write a detailed Korean Blogger article for the keyword '{keyword}'. "
            "Requirements: include a short intro, at least 4 body sections, practical examples, "
            "a short FAQ section with exactly 3 questions, and a closing summary limited to 2 paragraphs. "
            f"Use one of these title patterns with natural variation: {title_patterns}. "
            "Include one section for who should use it and one section for who may not need it. "
            "For each important tool or method, include when it works well and when it does not. "
            "Include at least 2 concrete everyday use cases such as meeting notes, email drafting, research summary, translation, or planning. "
            "Include at least one paragraph that begins with a cautious framing such as '다만', '반대로', or '굳이'. "
            "Include at least one specific observation that sounds like a person organizing a workflow, "
            "for example comparing a meeting-heavy day versus a translation-heavy day. "
            "Do not overuse bullet points. Mix short and medium-length paragraphs. "
            "Do not use hype phrases, motivational fluff, or repetitive transition phrases. "
            "Do not pretend to have personal real-world usage, but you may say '예를 들면', '실무에서는', or '보통은'. "
            "Avoid closing every section too neatly. It is okay for some paragraphs to end with a practical caution instead of a polished takeaway. "
            "Avoid textbook phrasing like '지금부터 알아보겠습니다', '정리해 보겠습니다', and repeated '도움이 됩니다'. "
            "If the keyword implies comparison or recommendation, explain selection criteria clearly. "
            "Title should be useful and search-friendly, not clickbait. "
            "Labels should be short and relevant. "
            "Meta description should be under 160 Korean characters. "
            "Your response must be a json object."
        )
        return {
            "model": model,
            "instructions": instructions,
            "input": user_prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "blog_post",
                    "strict": True,
                    "schema": self._response_schema(),
                }
            },
        }

    def _build_rewrite_payload(
        self, keyword: str, post: dict[str, object]
    ) -> dict[str, object]:
        model = self.config.openai_model or "gpt-5-mini"
        instructions = (
            "You are rewriting a Korean Blogger article draft about AI and productivity tools. "
            "Return only valid json with keys title, meta_description, content_html, labels. "
            "Preserve the meaning, search intent, and core structure, but make the prose sound more natural. "
            "Reduce repetitive sentence openings and stiff transitions. "
            "Keep practical examples, limitations, and tradeoffs. "
            "Do not add fake experiences, invented benchmarks, or unsupported claims. "
            "Remove phrases that sound like a school essay, brochure, or AI summary. "
            "Keep at least one cautious paragraph and at least one 'not for everyone' angle. "
            "Keep HTML valid and do not include markdown fences. "
            "Your response must be a json object."
        )
        draft_json = json.dumps(post, ensure_ascii=False)
        user_prompt = (
            f"Rewrite the draft for the keyword '{keyword}'. "
            "Make it sound like a careful human blogger who explains clearly without overperforming. "
            "Keep the helpful sections, but vary paragraph rhythm and wording. "
            "Avoid generic wrap-up sentences and brochure-like phrasing. "
            "Replace neat, summary-like sentences with more grounded wording when possible. "
            "If a paragraph feels too smooth or too perfect, make it a little more restrained and practical. "
            "Preserve concrete examples, selection criteria, FAQ count, and the 'who should use it / who may not need it' structure. "
            f"Current draft JSON: {draft_json}"
        )
        return {
            "model": model,
            "instructions": instructions,
            "input": user_prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "blog_post_rewrite",
                    "strict": True,
                    "schema": self._response_schema(),
                }
            },
        }

    def _response_schema(self) -> dict[str, object]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {"type": "string"},
                "meta_description": {"type": "string"},
                "content_html": {"type": "string"},
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["title", "meta_description", "content_html", "labels"],
        }

    def _send_payload(self, payload: dict[str, object], action: str) -> dict[str, object]:
        req = request.Request(
            self.RESPONSES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise OpenAIContentError(
                f"OpenAI content {action} failed with HTTP {exc.code}: {details}"
            ) from exc
        except URLError as exc:
            raise OpenAIContentError(
                f"OpenAI content {action} failed due to a network error: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise OpenAIContentError(
                f"OpenAI content {action} timed out after {self.timeout_seconds} seconds."
            ) from exc
        except socket.timeout as exc:
            raise OpenAIContentError(
                f"OpenAI content {action} timed out after {self.timeout_seconds} seconds."
            ) from exc

        return json.loads(body) if body else {}

    def _extract_post_json(
        self,
        response_json: dict[str, object],
        keyword: str,
        fallback: dict[str, object] | None = None,
    ) -> dict[str, object]:
        output = response_json.get("output", [])
        text_chunks: list[str] = []

        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    text_value = block.get("text")
                    if isinstance(text_value, str):
                        text_chunks.append(text_value)

        raw_text = "".join(text_chunks).strip()
        if not raw_text:
            raise OpenAIContentError("OpenAI response did not include output text.")

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise OpenAIContentError(
                f"OpenAI returned non-JSON content: {raw_text[:300]}"
            ) from exc

        content_html = parsed.get("content_html")
        if not isinstance(content_html, str) or not content_html.strip():
            parsed["content_html"] = (
                str(fallback.get("content_html"))
                if fallback and fallback.get("content_html")
                else build_draft_html(keyword)
            )
        if not isinstance(parsed.get("title"), str) or not str(parsed["title"]).strip():
            parsed["title"] = (
                str(fallback.get("title"))
                if fallback and fallback.get("title")
                else keyword
            )
        if not isinstance(parsed.get("meta_description"), str) or not str(
            parsed["meta_description"]
        ).strip():
            parsed["meta_description"] = (
                str(fallback.get("meta_description"))
                if fallback and fallback.get("meta_description")
                else build_meta_description(keyword)
            )
        labels = parsed.get("labels")
        if not isinstance(labels, list):
            parsed["labels"] = (
                list(fallback.get("labels"))
                if fallback and isinstance(fallback.get("labels"), list)
                else list(self.DEFAULT_LABELS)
            )
        parsed["title"] = self._cleanup_text(str(parsed["title"]))
        parsed["meta_description"] = self._cleanup_text(str(parsed["meta_description"]))
        parsed["content_html"] = self._cleanup_text(str(parsed["content_html"]))
        return parsed

    def _cleanup_text(self, value: str) -> str:
        cleaned = value
        for phrase in self.BANNED_PHRASES:
            cleaned = cleaned.replace(phrase, "")

        replacements = {
            "지금부터 알아보겠습니다": "이 부분부터 보면 됩니다",
            "정리해 보겠습니다": "정리하면 이렇습니다",
            "도움이 됩니다": "실제로는 꽤 유용합니다",
            "추천할 수 있습니다": "고려해볼 만합니다",
            "활용할 수 있습니다": "활용해볼 수 있습니다",
            "효율성을 극대화할 수 있습니다": "시간을 줄이는 데 도움이 될 수 있습니다",
        }
        for source, target in replacements.items():
            cleaned = cleaned.replace(source, target)

        cleaned = cleaned.replace("  ", " ").strip()
        return cleaned
