from __future__ import annotations

import json
import re
import socket
from urllib import request
from urllib.error import HTTPError, URLError

from autoblog.config import AppConfig
from autoblog.content.templates import build_draft_html, build_meta_description


class OpenAIContentError(RuntimeError):
    """Raised when OpenAI content generation fails."""


HEADING_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.IGNORECASE | re.DOTALL)


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
        "{keyword} 추천 전에 먼저 볼 기준",
        "{keyword} 실제 활용 정리",
        "{keyword} 어디까지 자동화할 수 있는지 정리",
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
        model = self.config.openai_model or "gpt-5.2"
        title_patterns = " / ".join(
            pattern.format(keyword=keyword) for pattern in self.TITLE_PATTERNS
        )
        instructions = (
            "You are generating a Korean Blogger post about AI and productivity tools. "
            "Return only valid json with keys title, meta_description, content_html, labels. "
            "The article must be useful, grounded, natural, and suitable for AdSense review. "
            "Do not include markdown fences. Use HTML in content_html with h2, h3, p, ul, li tags. "
            "Target Korean readers and write natural Korean that sounds like a practical blogger, not a brochure. "
            "Avoid unsupported promises and avoid made-up claims. "
            "Use specific situations, tradeoffs, limitations, and realistic caveats. "
            "Keep the article around 2200 to 3200 Korean characters in plain text, not a long essay. "
            "Do not sound overly polished, overly symmetrical, or repetitive."
        )
        user_prompt = (
            f"Write a Korean Blogger article for the keyword '{keyword}'. "
            "Requirements: include a short intro, 4 to 5 body sections, practical examples, "
            "a FAQ section with exactly 3 questions, and a closing summary limited to 2 short paragraphs. "
            f"Use one of these title patterns with natural variation: {title_patterns}. "
            "Title must feel natural in Korean, ideally 18 to 34 characters, and should not use an awkward comma break. "
            "Headings must also feel natural in Korean. Avoid headings like '키워드가 필요한 이유' or repetitive keyword stuffing. "
            "Prefer simple headings such as '먼저 볼 기준', '어디서 편한지', '장점과 한계'. "
            "Include one section for who should use it and one section for who may not need it. "
            "Include at least 2 concrete everyday use cases such as meeting notes, email drafting, research summary, translation, or planning. "
            "Include at least one paragraph that begins with a cautious framing such as '다만', '반대로', or '굳이'. "
            "Do not overuse bullet points. Mix short and medium-length paragraphs. "
            "Avoid hype phrases, generic transitions, and AI-summary tone. "
            "Do not pretend to have personal experience. "
            "Meta description should be under 150 Korean characters."
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

    def _build_rewrite_payload(self, keyword: str, post: dict[str, object]) -> dict[str, object]:
        model = self.config.openai_model or "gpt-5.2"
        instructions = (
            "You are rewriting a Korean Blogger article draft about AI and productivity tools. "
            "Return only valid json with keys title, meta_description, content_html, labels. "
            "Preserve the meaning and structure, but make the prose sound more natural. "
            "Reduce repetitive sentence openings and stiff transitions. "
            "Keep practical examples, limitations, and tradeoffs. "
            "Do not add fake experiences, invented benchmarks, or unsupported claims. "
            "Fix awkward titles or headings so they read naturally in Korean. "
            "Keep the full plain text roughly under 3200 Korean characters."
        )
        draft_json = json.dumps(post, ensure_ascii=False)
        user_prompt = (
            f"Rewrite the draft for the keyword '{keyword}'. "
            "Make it sound like a careful human blogger who explains clearly without overperforming. "
            "If the title sounds awkward, rewrite it into a simpler Korean search-friendly title. "
            "If any heading sounds stiff or repetitive, simplify it. "
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

        parsed["title"] = self._cleanup_title(str(parsed["title"]), keyword)
        parsed["meta_description"] = self._cleanup_text(str(parsed["meta_description"]))
        parsed["content_html"] = self._cleanup_html(str(parsed["content_html"]), keyword)
        return parsed

    def _cleanup_title(self, value: str, keyword: str) -> str:
        cleaned = self._cleanup_text(value)
        cleaned = re.sub(r"\s*,\s*", ": ", cleaned, count=1)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" .:-")
        if len(cleaned) > 34:
            cleaned = cleaned[:34].rstrip() + "…"
        if cleaned == keyword:
            cleaned = f"{keyword} 실제 활용 정리"
        return cleaned

    def _cleanup_html(self, value: str, keyword: str) -> str:
        cleaned = self._cleanup_text(value)
        cleaned = self._cleanup_headings(cleaned, keyword)
        plain_text = re.sub(r"<[^>]+>", " ", cleaned)
        plain_text = re.sub(r"\s+", " ", plain_text).strip()
        if len(plain_text) > 3200:
            cleaned = self._trim_html_paragraphs(cleaned, 3200)
        return cleaned

    def _cleanup_headings(self, html_value: str, keyword: str) -> str:
        def replacer(match: re.Match[str]) -> str:
            heading = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            heading = heading.replace(keyword, "").strip(" :-|")
            heading = re.sub(r"^(이 |그 )", "", heading).strip()
            replacements = {
                "가 필요한 이유": "먼저 볼 기준",
                "필요한 이유": "먼저 볼 기준",
                "핵심 기능": "어디서 편한지",
                "실제 활용 예시": "실제 활용 예시",
                "장단점": "장점과 한계",
                "추천 대상": "잘 맞는 사람",
                "faq": "자주 묻는 질문",
            }
            normalized = heading.lower()
            if normalized in replacements:
                heading = replacements[normalized]
            elif heading in replacements:
                heading = replacements[heading]
            if not heading:
                heading = "먼저 볼 기준"
            return f"<h2>{heading}</h2>"

        return HEADING_RE.sub(replacer, html_value)

    def _trim_html_paragraphs(self, html_value: str, max_chars: int) -> str:
        parts = re.split(r"(<p>.*?</p>)", html_value, flags=re.IGNORECASE | re.DOTALL)
        kept: list[str] = []
        current_len = 0
        for part in parts:
            plain = re.sub(r"<[^>]+>", " ", part)
            plain = re.sub(r"\s+", " ", plain).strip()
            if current_len + len(plain) > max_chars and part.lower().startswith("<p>"):
                continue
            kept.append(part)
            current_len += len(plain)
        return "".join(kept)

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

        return re.sub(r"\s{2,}", " ", cleaned).strip()
