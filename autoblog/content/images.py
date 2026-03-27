from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import quote


HEADING_BLOCK_RE = re.compile(r"(<h2[^>]*>.*?</h2>)", re.IGNORECASE | re.DOTALL)
HEADING_TEXT_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")

THEMES = [
    {
        "hero_start": "#0f172a",
        "hero_end": "#1d4ed8",
        "hero_panel": "#eff6ff",
        "hero_accent": "#2563eb",
        "hero_text": "#ffffff",
        "hero_sub": "#dbeafe",
        "hero_footer": "#bfdbfe",
        "card_bg": "#f8fafc",
        "card_panel": "#dbeafe",
        "card_accent": "#1d4ed8",
        "card_text": "#0f172a",
        "card_sub": "#475569",
        "table_bg": "#f8fafc",
        "table_header": "#1e40af",
        "table_panel": "#dbeafe",
        "table_cell": "#ffffff",
        "check_bg": "#eef2ff",
        "check_panel": "#1e293b",
        "check_sub": "#93c5fd",
    },
    {
        "hero_start": "#1f2937",
        "hero_end": "#0f766e",
        "hero_panel": "#ecfeff",
        "hero_accent": "#0f766e",
        "hero_text": "#ffffff",
        "hero_sub": "#ccfbf1",
        "hero_footer": "#99f6e4",
        "card_bg": "#f0fdfa",
        "card_panel": "#ccfbf1",
        "card_accent": "#0f766e",
        "card_text": "#134e4a",
        "card_sub": "#0f766e",
        "table_bg": "#f0fdfa",
        "table_header": "#115e59",
        "table_panel": "#ccfbf1",
        "table_cell": "#ffffff",
        "check_bg": "#ecfeff",
        "check_panel": "#164e63",
        "check_sub": "#67e8f9",
    },
    {
        "hero_start": "#111827",
        "hero_end": "#b45309",
        "hero_panel": "#fffbeb",
        "hero_accent": "#d97706",
        "hero_text": "#ffffff",
        "hero_sub": "#fde68a",
        "hero_footer": "#fcd34d",
        "card_bg": "#fffbeb",
        "card_panel": "#fde68a",
        "card_accent": "#b45309",
        "card_text": "#78350f",
        "card_sub": "#92400e",
        "table_bg": "#fff7ed",
        "table_header": "#9a3412",
        "table_panel": "#fed7aa",
        "table_cell": "#ffffff",
        "check_bg": "#fffbeb",
        "check_panel": "#78350f",
        "check_sub": "#fbbf24",
    },
]


def inject_inline_images(
    content_html: str,
    title: str,
    keyword: str,
    max_section_cards: int,
    output_dir: str = "",
    public_base_url: str = "",
) -> str:
    theme = _select_theme(keyword)
    image_plan = _select_image_plan(content_html, max_section_cards)
    asset_store = _AssetStore(
        title=title,
        keyword=keyword,
        output_dir=Path(output_dir) if output_dir else None,
        public_base_url=public_base_url,
    )

    hero = _image_block(
        asset_store,
        "hero",
        _svg_thumbnail(title, keyword, theme),
        alt=f"{title} 썸네일",
        class_name="hero-thumb",
    )
    with_section_cards = _inject_section_cards(
        content_html,
        image_plan["section_cards"],
        asset_store,
        theme,
    )

    tail_blocks: list[str] = []
    if image_plan["include_comparison"]:
        tail_blocks.append(
            _image_block(
                asset_store,
                "comparison",
                _svg_comparison_table(title, _extract_headings(content_html), theme),
                alt=f"{title} 비교표",
                class_name="comparison-table-card",
            )
        )
    if image_plan["include_checklist"]:
        tail_blocks.append(
            _image_block(
                asset_store,
                "checklist",
                _svg_checklist(title, theme),
                alt=f"{title} 체크리스트",
                class_name="checklist-card",
            )
        )

    tail_html = "\n".join(tail_blocks)
    if tail_html:
        return f"{hero}\n{with_section_cards}\n{tail_html}"
    return f"{hero}\n{with_section_cards}"


class _AssetStore:
    def __init__(
        self,
        title: str,
        keyword: str,
        output_dir: Path | None,
        public_base_url: str,
    ) -> None:
        self.output_dir = output_dir
        self.public_base_url = public_base_url.rstrip("/")
        seed = _slugify(f"{keyword}-{title}") or "post"
        self.base_name = seed[:80]

    def build_src(self, suffix: str, svg: str) -> str:
        if self.output_dir and self.public_base_url:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            file_name = f"{self.base_name}-{suffix}.svg"
            file_path = self.output_dir / file_name
            file_path.write_text(svg, encoding="utf-8")
            return f"{self.public_base_url}/{quote(file_name)}"
        return "data:image/svg+xml;utf8," + quote(svg, safe="")


def _inject_section_cards(
    content_html: str,
    max_section_cards: int,
    asset_store: _AssetStore,
    theme: dict[str, str],
) -> str:
    count = 0

    def replacer(match: re.Match[str]) -> str:
        nonlocal count
        heading_html = match.group(1)
        if count >= max_section_cards:
            return heading_html
        heading_text = _extract_heading_text(heading_html)
        count += 1
        card = _image_block(
            asset_store,
            f"section-{count}",
            _svg_section_card(heading_text, count, theme),
            alt=f"{heading_text} 섹션 카드",
            class_name="section-card",
        )
        return f"{heading_html}\n{card}"

    return HEADING_BLOCK_RE.sub(replacer, content_html)


def _select_image_plan(content_html: str, max_section_cards: int) -> dict[str, int | bool]:
    plain_text = _plain_text(content_html)
    word_count = len([token for token in plain_text.split(" ") if token.strip()])
    headings = _extract_headings(content_html)
    heading_count = len(headings)

    if word_count < 450:
        section_cards = min(2, max_section_cards, heading_count)
        include_comparison = False
        include_checklist = True
    elif word_count < 900:
        section_cards = min(3, max_section_cards, heading_count)
        include_comparison = True
        include_checklist = True
    else:
        section_cards = min(max_section_cards, heading_count)
        include_comparison = True
        include_checklist = True

    return {
        "section_cards": section_cards,
        "include_comparison": include_comparison,
        "include_checklist": include_checklist,
    }


def _image_block(
    asset_store: _AssetStore,
    suffix: str,
    svg: str,
    alt: str,
    class_name: str,
) -> str:
    src = asset_store.build_src(suffix, svg)
    return (
        f'<p class="{class_name}" style="text-align:center;margin:16px 0;">'
        f'<img src="{src}" alt="{html.escape(alt)}" '
        'style="max-width:100%;height:auto;border:0;" />'
        "</p>"
    )


def _svg_thumbnail(title: str, keyword: str, theme: dict[str, str]) -> str:
    title_lines = _wrap_text(title, 20, max_lines=2)
    subtitle = _trim_text(keyword, 32)
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="{theme["hero_start"]}"/>
      <stop offset="100%" stop-color="{theme["hero_end"]}"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" rx="36" fill="url(#bg)"/>
  <rect x="70" y="70" width="180" height="180" rx="28" fill="{theme["hero_panel"]}" opacity="0.95"/>
  <circle cx="160" cy="160" r="54" fill="{theme["hero_accent"]}"/>
  <rect x="132" y="106" width="56" height="108" rx="14" fill="{theme["hero_sub"]}"/>
  <rect x="320" y="110" width="780" height="84" rx="20" fill="#ffffff" opacity="0.1"/>
  <text x="320" y="260" fill="{theme["hero_text"]}" font-size="58" font-weight="700" font-family="Arial, sans-serif">{html.escape(title_lines[0])}</text>
  <text x="320" y="335" fill="{theme["hero_text"]}" font-size="58" font-weight="700" font-family="Arial, sans-serif">{html.escape(title_lines[1] if len(title_lines) > 1 else "")}</text>
  <text x="320" y="430" fill="{theme["hero_sub"]}" font-size="28" font-family="Arial, sans-serif">{html.escape(subtitle)}</text>
  <text x="85" y="565" fill="{theme["hero_footer"]}" font-size="24" font-family="Arial, sans-serif">AI Productivity Guide</text>
</svg>
""".strip()


def _svg_section_card(heading: str, index: int, theme: dict[str, str]) -> str:
    line = _trim_text(heading, 28)
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="240" viewBox="0 0 1200 240">
  <rect width="1200" height="240" rx="28" fill="{theme["card_bg"]}"/>
  <rect x="28" y="28" width="150" height="184" rx="22" fill="{theme["card_panel"]}"/>
  <text x="103" y="142" text-anchor="middle" fill="{theme["card_accent"]}" font-size="78" font-weight="700" font-family="Arial, sans-serif">{index}</text>
  <text x="220" y="100" fill="{theme["card_text"]}" font-size="42" font-weight="700" font-family="Arial, sans-serif">{html.escape(line)}</text>
  <text x="220" y="158" fill="{theme["card_sub"]}" font-size="22" font-family="Arial, sans-serif">Section overview</text>
</svg>
""".strip()


def _svg_comparison_table(title: str, headings: list[str], theme: dict[str, str]) -> str:
    left = _trim_text(title, 22)
    defaults = ["핵심 기능", "장단점", "선택 기준"]
    row_titles = headings[:3]
    while len(row_titles) < 3:
        row_titles.append(defaults[len(row_titles)])
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420">
  <rect width="1200" height="420" rx="28" fill="{theme["table_bg"]}"/>
  <rect x="40" y="40" width="1120" height="72" rx="18" fill="{theme["table_header"]}"/>
  <text x="72" y="86" fill="#ffffff" font-size="34" font-weight="700" font-family="Arial, sans-serif">{html.escape(left)} 비교 기준</text>
  <rect x="40" y="136" width="280" height="72" rx="12" fill="{theme["table_panel"]}"/>
  <rect x="340" y="136" width="360" height="72" rx="12" fill="{theme["table_panel"]}"/>
  <rect x="720" y="136" width="200" height="72" rx="12" fill="{theme["table_panel"]}"/>
  <rect x="940" y="136" width="220" height="72" rx="12" fill="{theme["table_panel"]}"/>
  <text x="70" y="182" fill="{theme["card_text"]}" font-size="28" font-weight="700" font-family="Arial, sans-serif">항목</text>
  <text x="370" y="182" fill="{theme["card_text"]}" font-size="28" font-weight="700" font-family="Arial, sans-serif">확인 포인트</text>
  <text x="750" y="182" fill="{theme["card_text"]}" font-size="28" font-weight="700" font-family="Arial, sans-serif">난이도</text>
  <text x="970" y="182" fill="{theme["card_text"]}" font-size="28" font-weight="700" font-family="Arial, sans-serif">추천 상황</text>
  {_table_row(226, _trim_text(row_titles[0], 12), "자동화 범위, 정확도, 연동성", "중", "업무 효율화", theme)}
  {_table_row(294, _trim_text(row_titles[1], 12), "시간 절약 vs 검토 필요", "중", "도입 검토", theme)}
  {_table_row(362, _trim_text(row_titles[2], 12), "사용 빈도, 예산, 적응 비용", "중", "툴 비교 글", theme)}
</svg>
""".strip()


def _table_row(y: int, col1: str, col2: str, col3: str, col4: str, theme: dict[str, str]) -> str:
    return (
        f'<rect x="40" y="{y}" width="280" height="52" rx="10" fill="{theme["table_cell"]}"/>'
        f'<rect x="340" y="{y}" width="360" height="52" rx="10" fill="{theme["table_cell"]}"/>'
        f'<rect x="720" y="{y}" width="200" height="52" rx="10" fill="{theme["table_cell"]}"/>'
        f'<rect x="940" y="{y}" width="220" height="52" rx="10" fill="{theme["table_cell"]}"/>'
        f'<text x="66" y="{y + 34}" fill="{theme["card_text"]}" font-size="24" font-family="Arial, sans-serif">{html.escape(col1)}</text>'
        f'<text x="366" y="{y + 34}" fill="{theme["card_text"]}" font-size="22" font-family="Arial, sans-serif">{html.escape(col2)}</text>'
        f'<text x="790" y="{y + 34}" fill="{theme["card_text"]}" font-size="24" font-family="Arial, sans-serif">{html.escape(col3)}</text>'
        f'<text x="966" y="{y + 34}" fill="{theme["card_text"]}" font-size="22" font-family="Arial, sans-serif">{html.escape(col4)}</text>'
    )


def _svg_checklist(title: str, theme: dict[str, str]) -> str:
    left = _trim_text(title, 24)
    items = ["핵심 기능 확인", "활용 예시 확인", "장단점 비교", "추천 대상 정리"]
    y_positions = [105, 165, 225, 285]
    item_text = []
    for y, item in zip(y_positions, items):
        item_text.append(
            f'<circle cx="420" cy="{y - 8}" r="11" fill="{theme["hero_accent"]}"/>'
            f'<text x="455" y="{y}" fill="{theme["card_text"]}" font-size="28" font-family="Arial, sans-serif">{html.escape(item)}</text>'
        )
    items_svg = "".join(item_text)
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="360" viewBox="0 0 1200 360">
  <rect width="1200" height="360" rx="28" fill="{theme["check_bg"]}"/>
  <rect x="36" y="36" width="300" height="288" rx="24" fill="{theme["check_panel"]}"/>
  <text x="72" y="120" fill="{theme["check_sub"]}" font-size="22" font-family="Arial, sans-serif">Quick checklist</text>
  <text x="72" y="190" fill="#ffffff" font-size="40" font-weight="700" font-family="Arial, sans-serif">{html.escape(left)}</text>
  {items_svg}
</svg>
""".strip()


def _wrap_text(value: str, max_chars: int, max_lines: int) -> list[str]:
    words = value.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
            if len(lines) == max_lines - 1:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    while len(lines) < max_lines:
        lines.append("")
    return [_trim_text(line, max_chars) for line in lines[:max_lines]]


def _trim_text(value: str, max_chars: int) -> str:
    value = value.strip()
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip() + "…"


def _extract_heading_text(value: str) -> str:
    match = HEADING_TEXT_RE.search(value)
    if not match:
        return _strip_tags(value)
    return _strip_tags(match.group(1))


def _strip_tags(value: str) -> str:
    return TAG_RE.sub("", value)


def _extract_headings(content_html: str) -> list[str]:
    headings: list[str] = []
    for match in HEADING_BLOCK_RE.finditer(content_html):
        heading = _extract_heading_text(match.group(1)).strip()
        if heading:
            headings.append(heading)
    return headings


def _plain_text(content_html: str) -> str:
    return WHITESPACE_RE.sub(" ", TAG_RE.sub(" ", content_html)).strip()


def _select_theme(seed: str) -> dict[str, str]:
    index = sum(ord(char) for char in seed) % len(THEMES)
    return THEMES[index]


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z가-힣]+", "-", value).strip("-").lower()
    return re.sub(r"-{2,}", "-", normalized)
