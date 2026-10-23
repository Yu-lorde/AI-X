"""去 AI 味检测器。只判断成稿是否带 AI 腔，不负责改写。

与 compliance.py 同形状：输入成稿，返回 issues 列表，交给 pipeline 的 rewrite
闭环处理。合规类问题（绝对化、虚假价格等）在 compliance.py，这里只管“读起来
像不像真人写的”。规则参考 humanizer-zh (op7418, MIT) 的 AI 写作特征，并按中文
营销软文裁剪，去掉了英文专有的特征（-ing 分析、系动词回避、标题大写、弯引号）
和对 JSON 成稿不适用的格式特征（加粗、内联列表标题等）。
"""

import re
import statistics

# ========================================================================
# 营销 AI 词黑名单（特征 #4 宣传广告式语言 / #7 过度用 AI 词汇）
# ------------------------------------------------------------------------
# 这是最常改动的一张表。软文高发的 AI / 营销腔套词，命中即提示换成具体表达。
# 想加词或删词，直接改这个元组即可，不影响任何其他逻辑。
# 偏保守可删掉下面几个较常用的动词（开启 / 遇见 / 解锁 等）。
# ========================================================================
MARKETING_AI_WORDS = (
    "赋能", "打造", "助力", "一键", "无缝", "极致", "焕新", "焕活",
    "尽享", "畅享", "沉浸式", "黑科技", "满满", "匠心", "倾力", "倾情",
    "全方位", "一站式", "值得拥有", "不容错过", "心动不已", "种草",
    "解锁", "开启", "遇见", "邂逅", "绽放", "点亮", "聚焦", "深耕",
    "生态", "闭环", "抓手", "链路", "护航", "加持",
)

# 填充短语（#22）：没有信息量、可直接删的套话。
FILLER_PHRASES = (
    "值得一提的是", "需要注意的是", "众所周知", "不难发现", "不得不说",
    "说到底", "一言以蔽之", "毫无疑问", "显而易见", "换句话说", "平心而论",
)

# 结尾套话 / 通用积极结论（#24）：只在文末一段 + 行动引导里检测。
ENDING_CLICHES = (
    "总之", "综上", "总而言之", "归根结底", "不失为", "不二之选",
    "理想之选", "明智之选", "值得信赖的选择", "还在等什么",
)

# 开头套话（#1）：只在导语 / 第一段开头检测。
OPENING_RE = re.compile(r"^(在当今|在这个|如今|随着.{0,12}(发展|到来|普及|升级)|在.{0,8}时代)")

# 模糊归因（#5）：没有 P1 依据的“权威背书”。
VAGUE_ATTRIBUTION = (
    "专家表示", "专家认为", "业内人士", "相关人士", "有研究表明",
    "众多用户反馈", "权威机构", "数据显示",
)

# ========================================================================
# 元话术 / 免责声明（方向 A 核心规则）
# ------------------------------------------------------------------------
# 把“证据边界、不确定、来源出处”暴露给读者的质检台词。它们是内部纪律，
# 只能进 pending，绝不进正文。命中即触发重写删除。跨场景、跨平台通用。
# ========================================================================
META_DISCLAIMER_WORDS = (
    "我不编", "不瞎写", "不替它", "没拿到", "我这次看的", "我查的时候",
    "无法确认", "无法核实", "未能确认", "没有确认",
    "未获取", "没有获取", "暂无", "暂未",
    "已下架", "没有公开", "未公开", "没有当前公开",
    "官方定位", "官方公开定位", "定位里写", "资料里写的是", "资料显示",
)
META_DISCLAIMER_RE = (
    re.compile(r"以[^，。、！？]{0,12}为准"),               # 以官网 / 商城 / 实际销售版本为准
    re.compile(r"资料(里|中)?[^，。、！？]{0,6}(没|未|无)"),  # 资料没给 / 资料里没写 / 资料未提供
    re.compile(r"具体[^，。、！？]{0,10}(没给|没有|得看|以)"),  # 具体数字没给 / 具体以……
    re.compile(r"(数字|参数|配置|规格)[^，。、！？]{0,6}(没给|没有|资料没)"),
)

# 否定式排比（#9）：不仅…更 / 不只…还 / 不是…而是，典型 AI 腔。
NEGATION_PARALLEL_RE = (
    re.compile(r"不仅[^。！？]{0,20}(更|还|也|而且)"),
    re.compile(r"不只[^。！？]{0,20}(更|还|也)"),
    re.compile(r"不是[^。！？]{0,15}而是"),
    re.compile(r"不是[^。！？]{0,30}但"),
)

# 口水收尾/过渡套话（结构性 AI 腔的常见零件）。
SPOKEN_CLICHES = ("接得住", "不掉链子", "不费劲", "用下来", "图的就是", "加分项", "说点限制")

# 逐项罗列（最典型的 AI 结构）：多段用“X这块 / X方面 / 说点X / 至于X”当方面名开头。
ASPECT_OPENER_RE = re.compile(r"^.{0,7}(这块|方面)[，,]|^说点|^至于")
MIN_ASPECT_OPENERS = 3

# 虚假范围（#12）：从 X 到 Y。单处可接受，密度高才判。
RANGE_RE = re.compile(r"从[^，。、！？]{1,8}到[^，。、！？]{1,10}")

# 三段式排比（#10）：三个 2-6 字短项并列，如“高效、轻薄、持久”。前后用边界约束
# （两端都不是汉字），避免把句子中嵌着的真实功能名长列表（…的指纹识别、华为分享…）
# 误切成三连；只命中标点/句首包起来的独立并列。
RULE_OF_THREE_RE = re.compile(
    r"(?<![一-鿿])[一-鿿]{2,4}[，、][一-鿿]{2,4}[，、][一-鿿]{2,4}(?![一-鿿])"
)

# emoji（#17，平台相关）：小红书 / 微博靠 emoji 造氛围，这两个平台不检测。
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F0FF⬀-⯿]")
EMOJI_FRIENDLY_PLATFORMS = ("小红书", "微博")

# 破折号过度（#13，可选，阈值较高，中文少用）。
DASH_RE = re.compile(r"——")

# 句长方差（humanizer-zh 核心规则 3：节奏）。句子太少不判。
MIN_SENTENCES_FOR_BURST = 5
BURST_STD_THRESHOLD = 3.0  # 偏保守：只判明显机械、句长几乎一致的文本，放过正常短句
SENTENCE_SPLIT_RE = re.compile(r"[。！？!?\n]+")


def check_style(article: dict, platform: str, source_text: str = "") -> list[str]:
    """检测成稿 AI 腔，返回问题列表（空列表表示通过）。只读不改。

    source_text 是本次 P1 原文：命中的营销词若在 P1 里本就存在（如官方功能名
    “一键还原”），说明是真实产品术语而非 AI 腔，不计入。
    """
    issues: list[str] = []
    lead = (article.get("lead") or "").strip()
    paragraphs = [str(p).strip() for p in (article.get("paragraphs") or []) if str(p).strip()]
    cta = (article.get("cta") or "").strip()
    text = "\n".join(part for part in [lead, *paragraphs, cta] if part)
    tail = ((paragraphs[-1] if paragraphs else "") + cta).strip()

    hit_words = [w for w in MARKETING_AI_WORDS if w in text and w not in source_text]
    if hit_words:
        issues.append(f"AI味：营销套词「{'、'.join(hit_words[:6])}」，换成具体说法或删掉。")

    hit_filler = [w for w in FILLER_PHRASES if w in text]
    if hit_filler:
        issues.append(f"AI味：填充短语「{'、'.join(hit_filler)}」没有信息量，删掉直接说。")

    if OPENING_RE.search(lead) or (paragraphs and OPENING_RE.search(paragraphs[0])):
        issues.append("AI味：开头是「在当今 / 随着…」式套话，换成具体场景、画面或结果开场。")

    hit_end = [w for w in ENDING_CLICHES if w in tail]
    if hit_end:
        issues.append(f"AI味：结尾是「{'、'.join(hit_end)}」式总结套话，去掉或换成具体收束。")

    hit_attr = [w for w in VAGUE_ATTRIBUTION if w in text]
    if hit_attr:
        issues.append(f"AI味：模糊归因「{'、'.join(hit_attr)}」，要么对上 P1 依据，要么删掉。")

    hit_meta = [w for w in META_DISCLAIMER_WORDS if w in text]
    if hit_meta or any(r.search(text) for r in META_DISCLAIMER_RE):
        sample = "、".join(hit_meta[:6]) or "资料没给 / 以官网为准 / 具体得看"
        issues.append(f"AI味：正文出现免责/元话术「{sample}」，删掉——不确定的不写，只放进待确认，别向读者解释证据边界。")

    if any(r.search(text) for r in NEGATION_PARALLEL_RE):
        issues.append("AI味：出现「不仅…更…/不是…而是…/不是…但…」式转折排比，改成平铺直叙。")

    hit_spoken = [w for w in SPOKEN_CLICHES if w in text]
    if hit_spoken:
        issues.append(f"AI味：口水套话「{'、'.join(hit_spoken)}」，删掉或换成具体说法。")

    if sum(1 for p in [lead, *paragraphs] if ASPECT_OPENER_RE.search(p.strip())) >= MIN_ASPECT_OPENERS:
        issues.append("AI味：多段用“X这块/X方面/说点X”逐项罗列配置，改成按真实使用情节连贯叙述，挑 2–3 个重点写具体情节，不要逐项过参数。")

    if len(RANGE_RE.findall(text)) >= 2:
        issues.append("AI味：多处「从…到…」排比，保留最多一处，其余改写。")

    # 三词并列：只判“凑出来的形容词三连”。三项若都能在 P1 原文找到（真实功能名/术语
    # 的枚举，如“指纹识别、华为电脑管家、华为分享”），不算 AI 腔。比对前剥掉被正则黏进
    # 第一项的首字连接词（的/是/它…），否则“的指纹识别”会对不上原文。
    particles = set("的了和与及是也还又就把这那其我你它他啊呢只能")
    triples = []
    for m in RULE_OF_THREE_RE.finditer(text):
        items = [it for it in re.split(r"[，、]", m.group(0)) if it]
        cores = [(it[1:] if it and it[0] in particles else it) for it in items]
        if len(items) >= 3 and not all(c in source_text for c in cores):
            triples.append(m.group(0))
    if triples:
        named = "」「".join(dict.fromkeys(triples))
        issues.append(f"AI味：三词并列「{named}」，每一处都要拆开写或改成具体句子，不许三项短词并列。")

    if platform not in EMOJI_FRIENDLY_PLATFORMS and EMOJI_RE.search(text):
        issues.append(f"AI味：{platform} 成稿里出现 emoji，该平台不需要，删掉。")

    if len(DASH_RE.findall(text)) >= 3:
        issues.append("AI味：破折号过多，中文少用，改成句号或逗号。")

    burst_text = "。".join([lead, *paragraphs])
    sentences = [s for s in SENTENCE_SPLIT_RE.split(burst_text) if s.strip()]
    lengths = [len(s) for s in sentences]
    if len(lengths) >= MIN_SENTENCES_FOR_BURST and statistics.pstdev(lengths) < BURST_STD_THRESHOLD:
        issues.append("AI味：句子长度过于均匀，读起来机械，长短句交错、加一两个短句。")

    return issues
