import re

ABSOLUTE_WORDS = (
    "最强",
    "最佳",
    "最优",
    "唯一",
    "绝对",
    "完美",
    "顶级",
    "无敌",
    "吊打",
    "碾压",
    "完胜",
    "全网最低",
    "史上",
    "永久",
    "国家级",
)

# 「第一」只在真正的排名/销量断言里算绝对化，"开学第一周/第一次"这类不算。
ABSOLUTE_FIRST_RE = re.compile(r"(销量|市场|全球|全国|行业|口碑|份额|排名|全网)\s*第一|第一\s*(品牌|名牌|梯队)")

EXPERIENCE_WORDS = ("我用了", "亲测", "用了一个月", "我家", "个人感受", "真实体验")
PROMO_WORDS = ("补贴", "优惠券", "限时", "库存", "销量", "好评如潮", "赠品", "返点")
PRICE_RE = re.compile(r"(￥|¥)\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*元")

# 参数核验：数字 + 规格单位。成稿里的这类参数必须能在 P1 资料里找到对应数字，
# 否则多半是从参考范文（别的机型）搬来的，判为无依据。长单位排在前面优先匹配。
SPEC_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*"
    r"(nits?|尼特|Wh|GB|TB|GHz|MHz|Hz|万像素|英寸|寸|mAh|kg|mm|ppi|核|线程|代|K|%|W)",
    re.IGNORECASE,
)


def check_text(text: str, source_text: str, platform: str) -> list[str]:
    issues = []
    source_norm = re.sub(r"[,，]", "", source_text)  # 去千分位，避免 5799 对不上 5,799
    source_numbers = set(re.findall(r"\d+(?:\.\d+)?", source_norm))  # 按完整数字比对，避免 120 命中 1200
    for word in ABSOLUTE_WORDS:
        if word in text:
            issues.append(f"合规：出现绝对化或贬低用语「{word}」，需要删除。")
    if ABSOLUTE_FIRST_RE.search(text):
        issues.append("合规：出现「第一」类排名断言，需要删除或改为有依据的客观表述。")
    if platform == "小红书":
        for word in EXPERIENCE_WORDS:
            if word in text:
                issues.append(f"合规：小红书文案出现「{word}」，不能写成个人体验。")
    for word in PROMO_WORDS:
        if word in text and word not in source_text:
            issues.append(f"合规：写了「{word}」，本次检索资料中没有对应依据。")
    for match in PRICE_RE.finditer(text):
        token = match.group(0)
        number = re.sub(r"[^\d.]", "", token)
        if number and number not in source_numbers:
            issues.append(f"合规：出现价格「{token.strip()}」，资料原文中没有这个数字。")
    seen = set()
    for match in SPEC_RE.finditer(text):
        number, token = match.group(1), match.group(0).strip()
        if number in source_numbers or token in seen:
            continue
        seen.add(token)
        issues.append(f"合规：参数「{token}」在 P1 资料里找不到依据，可能来自参考范文的其他机型，请改用知识库里的参数或删除。")
    return issues
