"""把一句话需求解析成型号、人群、场景和平台四个字段，额外要求并入 note。

场景和平台严格限定在 strategy 的枚举内，解析不出就留空，交给现有追问机制处理。
型号只从原句抽取，不允许补造，否则 P1 会取不到对应的产品事实。
"""

from llm_client import chat_json
from strategy import MARKETING_SCENES, PERSPECTIVES, PLATFORMS, canonical_platform

_SYSTEM = """你是华为PC营销软文智能体的需求解析器。把用户的一句话需求拆成结构字段，只抽取句子里出现的信息，绝不编造。

字段说明：
- product：产品型号，只抽句子里明确写出的型号（例如 MateBook D 14）。句子没写具体型号就留空字符串，不要补造，也不要只填系列名。
- audience：目标人群，用句子里的说法填（例如 大学新生、经常出差的销售、学校信息中心）。没写就留空。
- scene：业务场景，必须从下面的候选里选最接近的一个：{scenes}。都不接近就留空，不要造新词；留空时把原话里的场景说法并进 note。
- platform：发布平台，必须从下面的候选里选最接近的一个：{platforms}。都不接近就留空，不要造新词。
- perspective：写作视角，只有句子明确表达了立场时才从候选里选：{perspectives}。没有明确说就留空，不要猜。
- note：把两部分合并写进来——(1) 没能对上上面字段的原话要素（例如没对上候选的场景说法、特殊人群补充）；(2) 额外写作要求（例如“重点说续航”“别提价格”“语气轻松一点”）。都没有就留空。

只输出一个 JSON 对象，不要 Markdown 代码块：
{{"product": "", "audience": "", "scene": "", "platform": "", "perspective": "", "note": ""}}
"""


def parse_request(sentence: str) -> dict:
    """调大模型把一句话抽成四字段 + note。LLM 不可用时由 llm_client 抛 LlmError。"""
    system = _SYSTEM.format(scenes="、".join(MARKETING_SCENES), platforms="、".join(PLATFORMS), perspectives="、".join(PERSPECTIVES))
    raw = chat_json(system, f"一句话需求：{sentence.strip()}")
    if not isinstance(raw, dict):
        raw = {}
    return _normalize(raw)


def _normalize(raw: dict) -> dict:
    def text(key: str) -> str:
        value = raw.get(key)
        return str(value).strip() if value is not None else ""

    scene = text("scene")
    if scene not in MARKETING_SCENES:
        scene = ""
    platform = canonical_platform(text("platform"))
    if platform not in PLATFORMS:
        platform = ""
    perspective = text("perspective")
    if perspective not in PERSPECTIVES:
        perspective = ""
    return {
        "product": text("product"),
        "audience": text("audience"),
        "scene": scene,
        "platform": platform,
        "perspective": perspective,
        "note": text("note"),
    }
