import re

ABSOLUTE_WORDS = (
    "最强",
    "最佳",
    "最优",
    "第一",
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
    "100%",
    "永久",
    "国家级",
)

EXPERIENCE_WORDS = ("我用了", "亲测", "用了一个月", "我家", "个人感受", "真实体验")
PROMO_WORDS = ("补贴", "优惠券", "限时", "库存", "销量", "好评如潮", "赠品", "返点")
PRICE_RE = re.compile(r"(￥|¥)\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*元")


def check_text(text: str, source_text: str, platform: str) -> list[str]:
    issues = []
    for word in ABSOLUTE_WORDS:
        if word in text:
            issues.append(f"合规：出现绝对化或贬低用语「{word}」，需要删除。")
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
        if number and number not in source_text:
            issues.append(f"合规：出现价格「{token.strip()}」，资料原文中没有这个数字。")
    return issues
