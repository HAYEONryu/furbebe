"""One representative coat tag; longest color tokens avoid substring collisions."""

import re

FAMILIES = {
    "grey": "회색 실버 청회색 회색빛 어두운회색 울프그레이 그레이 그레이색 grey gray silver",
    "brown": "연갈색 옅은갈색 갈색 밤색 진갈색 적갈색 브라운 붉은갈색 황갈색 흑갈색 "
    "금색 금갈색 레몬색 주황색 주황 적갈 황갈 탄색 탄 brown tan gold lemon orange",
    "cream": "크림색 크림 베이지색 베이지 연베이지 옅은황색 연한황색 cream beige",
    "black": "검정색 검정 검은색 검은 흑색 흑 black",
    "white": "흰색 흰 백색 백 화이트 하양 white",
}
TOKENS = {token: family for family, names in FAMILIES.items() for token in names.split()}
COLOR = re.compile(
    "|".join(
        (r"(?<![가-힣a-z])" + re.escape(token) + r"(?![가-힣a-z])")
        if len(token) == 1 or token.isascii()
        else r"\s*".join(map(re.escape, token))
        for token in sorted(TOKENS, key=len, reverse=True)
    )
)
PATTERN = re.compile(r"반점|얼룩(?:무늬)?|점박|점무늬|호반색|호랑이무늬|호피|브린들|brindle")


def classify(text):
    compact = " ".join((text or "").lower().split())
    families = {TOKENS[re.sub(r"\s+", "", match.group())] for match in COLOR.finditer(compact)}
    if "흑백" in compact:
        families.update(("black", "white"))
    # User override: any grey combination is unmatched, even with a pattern.
    if "grey" in families:
        return None, True
    if PATTERN.search(re.sub(r"\s+", "", compact)) or len(families) >= 3:
        return "patterned_coat", True
    if families == {"black", "white"}:
        return "cookies_cream", True
    if "brown" in families:
        return "brownie", True
    if "cream" in families:
        return "cream_coat", True
    if families == {"black"}:
        return "black_coat", True
    if families == {"white"}:
        return "white_coat", True
    return None, False


def pick_color(color, special):
    key, recognized = classify(color)
    if recognized:
        return (key, f"color_text: {color}") if key else None
    # Free prose fallback excludes medical spots and colors of accessories.
    candidates = []
    for clause in re.split(r"[.,;/|!?\n\r]+", special or ""):
        if re.search(r"피부|눈|상처|오염|목줄|옷|리드줄|하네스|아닌|아님|없", clause):
            continue
        candidates.append(clause.strip())
    description = ", ".join(candidates)
    key, _ = classify(description)
    return (key, f"special_mark: {description}") if key else None
