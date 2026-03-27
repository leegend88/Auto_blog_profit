from __future__ import annotations

def build_post_outline(keyword: str) -> list[str]:
    return [
        f"{keyword}가 필요한 이유",
        f"{keyword} 핵심 기능",
        f"{keyword} 실제 활용 예시",
        f"{keyword} 장단점",
        f"{keyword} 추천 대상",
        f"{keyword} FAQ",
    ]


def build_draft_html(keyword: str) -> str:
    outline = build_post_outline(keyword)
    sections = "\n".join(
        f"<h2>{heading}</h2>\n<p>이 섹션은 추후 LLM 본문 생성 결과로 교체됩니다.</p>"
        for heading in outline
    )
    return (
        f"<p><strong>{keyword}</strong>를 주제로 생성된 초안입니다.</p>\n"
        f"{sections}\n"
        "<p>결론: 실사용 관점에서 정리하고, 초보자에게 도움이 되는 팁을 추가합니다.</p>"
    )


def build_meta_description(keyword: str) -> str:
    return (
        f"{keyword}를 처음 쓰는 사람도 이해하기 쉽게 정리한 실전 가이드입니다. "
        "핵심 기능, 활용 예시, 추천 대상까지 한 번에 확인하세요."
    )
