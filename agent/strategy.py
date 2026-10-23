"""发布平台的交付格式。场景内容不在这里编写，必须从 P8 文档读取。"""

MARKETING_SCENES = ["开学季", "职场办公", "内容创作", "家庭换新", "企业采购", "门店到访", "新品首发", "节日营销", "无明确"]

# 只记录 P6/02 的文档名称，用来从 ima 检索。篇幅、结构和图片数量以取回的模板原文为准。
# image_min / image_max 对齐 P6/02 平台模板里的图文节奏，检索不足时按实际张数配，并在核验里说明。
PLATFORMS = {
    "微信公众号": {"query": "微信公众号长图文创作指南", "file": "微信公众号图文模板", "match": ["微信公众号"], "tags": False, "image_min": 4, "image_max": 6},
    "小红书": {"query": "小红书图文创作指南", "file": "小红书图文模板", "match": ["小红书"], "tags": True, "image_min": 6, "image_max": 8},
    "销售朋友圈": {"query": "销售朋友圈创作指南", "file": "销售朋友圈模板", "match": ["销售朋友圈"], "tags": False, "image_min": 3, "image_max": 5},
    "门店海报": {"query": "门店长图与海报创作指南", "file": "门店海报图文模板", "match": ["海报"], "tags": False, "image_min": 1, "image_max": 1},
    "知乎": {"query": "知乎问答创作指南", "file": "知乎图文模板", "match": ["知乎"], "tags": False, "image_min": 2, "image_max": 4},
    "微博": {"query": "微博创作指南", "file": "微博图文模板", "match": ["微博"], "tags": True, "image_min": 1, "image_max": 6},
    "新闻稿": {"query": "新闻稿创作指南", "file": "新闻稿图文模板", "match": ["新闻稿"], "tags": False, "image_min": 1, "image_max": 3},
    "抖音短视频": {"query": "抖音创作指南", "file": "抖音短视频模板", "match": ["抖音"], "tags": False, "image_min": 3, "image_max": 6},
    "微信视频号": {"query": "微信视频号创作指南", "file": "微信视频号模板", "match": ["视频号"], "tags": False, "image_min": 3, "image_max": 6},
    "B站中长视频": {"query": "B站中长视频创作指南", "file": "B站中长视频模板", "match": ["B站"], "tags": False, "image_min": 2, "image_max": 4},
    "短视频口播": {"query": "通用短视频创作指南", "file": "短视频口播图文模板", "match": ["短视频"], "tags": False, "image_min": 3, "image_max": 6},
    "直播讲解": {"query": "直播创作指南", "file": "直播讲解模板", "match": ["直播"], "tags": False, "image_min": 2, "image_max": 4},
    "企业采购方案": {"query": "企业采购方案创作指南", "file": "企业采购方案模板", "match": ["企业采购方案"], "tags": False, "image_min": 2, "image_max": 4},
}
PLATFORM_ALIASES = {"公众号": "微信公众号", "门店朋友圈": "销售朋友圈", "朋友圈": "销售朋友圈"}

# 写作视角：决定成稿的叙述立场和切入角度，不突破合规。
# “真实用户”只是从用户的使用场景和体感角度写，仍不得杜撰体验数据或结论，参数只来自 P1。
PERSPECTIVES = {
    "真实用户": "以真实使用者的第一人称视角写：从具体使用场景、动作和体感切入，像用户在分享自己的使用过程；但不得杜撰未经证实的体验数据、测试结果或使用结论，参数只来自 P1。",
    "官方宣传": "以品牌官方视角写：从产品定位、核心能力和适用人群切入，陈述克制准确、代表官方口径，不堆营销套词，不替用户编造体验。",
    "媒体报道": "以第三方媒体或评测视角写：客观中立，交代背景和事实，明确区分官方信息与外部观察，不替品牌喊口号，不下未经证实的结论。",
    "行业分析": "以行业或选型顾问视角写：结合使用场景与需求做分析和取舍判断，给出选型逻辑而非单向推荐，指出适用与不适用的边界。",
}
PERSPECTIVE_DEFAULT = "真实用户"


def canonical_perspective(perspective: str) -> str:
    name = (perspective or "").strip()
    return name if name in PERSPECTIVES else PERSPECTIVE_DEFAULT


def perspective_brief(perspective: str) -> str:
    return PERSPECTIVES[canonical_perspective(perspective)]

EXTRA_MODEL_WORDS = ("se", "pro", "fold", "gt", "ultra", "酷睿", "优享", "行业版", "非凡")
# 价格卡只讲价格口径和下架状态，不是规格事实源，放进来会让成稿写成价格免责文。
# 价格由专门字段处理，不混进产品事实喂给模型。
FACT_HINTS = ("产品事实", "规格", "参数", "卖点与限制", "图片索引")
REJECT_HINTS = ("软文", "小红书", "公众号", "朋友圈", "海报", "案例研究", "话术", "完整参考案例", "问题清单", "客户画像", "价格")


def missing_questions(product: str, audience: str, scene: str, platform: str) -> list[str]:
    # 只有型号和平台是必填：型号决定 P1 取数，平台决定成稿形态。
    # 人群和场景可留空；留空或选「无明确」时按通用产品软文生成。
    questions = []
    if not product.strip():
        questions.append("要写哪一个具体型号？系列名不够，例如需要区分 MateBook 14 和 MateBook D 14。")
    if canonical_platform(platform) not in PLATFORMS:
        questions.append("发布平台须是 P6/02 中的模板：" + "、".join(p for p in PLATFORMS))
    return questions


def canonical_platform(platform: str) -> str:
    return PLATFORM_ALIASES.get(platform, platform)


def platform_rules(platform: str) -> dict:
    key = canonical_platform(platform)
    rule = PLATFORMS[key]
    return {
        "platform": key,
        "template_query": rule["query"],
        "template_file": rule["file"],
        "template_match": rule["match"],
        "use_tags": rule["tags"],
        "image_min": rule["image_min"],
        "image_max": rule["image_max"],
    }


def _norm(text: str) -> str:
    """去掉空格和连字符，让 hwpc_matebook-d-14 这类图片文件名能对上型号。"""
    return "".join(ch for ch in text.lower() if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")


def classify_title(product: str, title: str) -> str:
    """返回 exact、nearby 或 no。相近型号不能拿来补参数。"""
    product_n = _norm(product)
    title_n = _norm(title)
    if not product_n or product_n not in title_n:
        return "no"
    for word in EXTRA_MODEL_WORDS:
        word_n = _norm(word)
        if word_n in title_n and word_n not in product_n:
            return "nearby"
    return "exact"


def is_product_fact(title: str) -> bool:
    if any(word in title for word in REJECT_HINTS):
        return False
    return any(word in title for word in FACT_HINTS) or "P1" in title
