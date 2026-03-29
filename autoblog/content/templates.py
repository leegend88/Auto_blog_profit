from __future__ import annotations


def build_post_outline(keyword: str) -> list[str]:
    return [
        "먼저 볼 기준",
        "어디서 편해지는지",
        "실제 활용 예시",
        "장점과 한계",
        "잘 맞는 사람과 애매한 경우",
        "자주 묻는 질문",
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
        "<p>마무리: 실제로 써볼 때 편한 지점과 애매한 지점을 함께 정리합니다.</p>"
    )


def build_meta_description(keyword: str) -> str:
    return (
        f"{keyword}를 처음 보는 사람도 이해하기 쉽게 정리한 실전 가이드입니다. "
        "활용 예시, 장점과 한계, 추천 대상을 한 번에 확인할 수 있습니다."
    )
