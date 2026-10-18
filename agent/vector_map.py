"""把一句话映射到型号、人群、场景和平台。

文本先切成二字、三字片段，做成向量，再和目录里的条目算余弦相似度。
句子里写明了型号、场景或平台时，在相似度上加分，避免相近型号抢匹配。
"""

import math
import re
from collections import Counter

from scenario_catalog import MODULES
from strategy import MARKETING_SCENES, PLATFORMS, _norm, classify_title

# 只收录本地 P1 有产品事实的型号。别名用于精确命中，描述只参与向量相似度。
PRODUCTS = (
    ("MateBook D 14", ["MateBook D 14", "MateBookD14", "D14"], "Windows 入门轻薄本 防眩光护眼屏"),
    ("MateBook D 16", ["MateBook D 16", "MateBookD16", "D16"], "十六英寸大屏 标压"),
    ("MateBook D 16 SE 版", ["MateBook D 16 SE 版", "MateBook D 16 SE", "D16 SE", "D16SE"], "D16 SE 大屏"),
    ("MateBook 14 酷睿 Ultra", ["MateBook 14 酷睿 Ultra", "MateBook 14 酷睿"], "酷睿 Ultra 触控手写 生产力屏"),
    ("HUAWEI MateBook 14", ["HUAWEI MateBook 14", "鸿蒙 MateBook 14", "MateBook 14"], "鸿蒙 云晰柔光 主流笔记本"),
    ("HUAWEI MateBook Pro", ["HUAWEI MateBook Pro", "MateBook Pro"], "鸿蒙 柔性 OLED 轻薄"),
    ("HUAWEI MateBook Pro S", ["HUAWEI MateBook Pro S", "MateBook Pro S"], "旗舰 灵盾防窥 柔性 OLED"),
    ("HUAWEI MateBook Fold 非凡大师", ["MateBook Fold 非凡大师", "MateBook Fold", "非凡大师"], "折叠屏 非凡大师"),
    ("MateBook X系列", ["MateBook X Pro", "MateBook X系列", "MateBook X"], "旗舰轻薄 微绒"),
    ("MateBook GT 系列", ["MateBook GT 14", "MateBook GT"], "高性能 天王星散热"),
)

SCENE_ALIASES = {
    "开学季": ["开学季", "开学", "入学", "新学期"],
    "职场办公": ["职场办公", "职场", "出差办公", "通勤"],
    "内容创作": ["内容创作", "创作场景"],
    "家庭换新": ["家庭换新", "换新", "换电脑"],
    "企业采购": ["企业采购", "集采", "批量采购", "招标"],
    "门店到访": ["门店到访", "到店", "进店体验"],
    "新品首发": ["新品首发", "新品发布", "首发"],
    "节日营销": ["节日营销", "双十一", "春节档", "中秋"],
}

PLATFORM_ALIASES = {
    "微信公众号": ["微信公众号", "公众号", "订阅号"],
    "小红书": ["小红书"],
    "销售朋友圈": ["销售朋友圈", "朋友圈"],
    "门店海报": ["门店海报", "海报"],
    "知乎": ["知乎"],
    "微博": ["微博"],
    "新闻稿": ["新闻稿"],
    "抖音短视频": ["抖音短视频", "抖音"],
    "微信视频号": ["微信视频号", "视频号"],
    "B站中长视频": ["B站中长视频", "B站", "bilibili"],
    "短视频口播": ["短视频口播", "口播"],
    "直播讲解": ["直播讲解", "直播"],
    "企业采购方案": ["企业采购方案", "采购方案"],
}

# 口语说法只放进向量，不写进关键词表，避免把场景路由改松。
AUDIENCE_HINTS = {
    "01-政府机关": "公务员 机关 政务外网 公文处理",
    "02-央国企": "央企 国企总部 集团统一采购",
    "03-制造业": "车间 产线 工厂办公",
    "04-金融": "银行网点 证券 保险 柜员",
    "05-医疗": "医生 护士 医院信息科 门诊",
    "06-教育管理": "学校教务 教务处 电教 校园网 排课 机房 信息中心老师",
    "07-高校教师": "大学老师 备课 上课 高校教师",
    "08-高校学生": "大学新生 大学生 宿舍 课程作业 校园生活",
    "09-中小学教师": "中学老师 小学老师 班主任 课堂",
    "10-中小学生家庭": "家长 孩子上网课 中小学生 家庭作业",
    "11-科研机构": "实验室 课题组 研究生 科研",
    "12-软件开发": "程序员 写代码 开发 版本管理",
    "13-设计创意": "设计师 平面 视觉 海报 做图 视觉同学",
    "14-视频制作": "剪辑师 编导 摄像 做视频",
    "15-媒体编辑": "记者 编辑部 采编",
    "16-咨询服务": "咨询顾问 项目交付 出差汇报",
    "17-法律服务": "律师 律所 案件材料",
    "18-财税审计": "会计 出纳 报税 审计底稿",
    "19-房地产": "置业顾问 案场 带看",
    "20-建筑工程": "工地 施工图 项目部",
    "21-零售门店": "导购 门店店员 收银台",
    "22-酒店文旅": "酒店前台 文旅 住客",
    "23-交通物流": "物流调度 运输 车队",
    "24-电商运营": "网店 店铺运营 电商客服 直播带货",
    "25-销售团队": "销售跑业务 客户拜访 谈客户",
    "26-人力资源": "人事 招聘 入职办理",
    "27-行政管理": "行政专员 办公室 会议资产",
    "28-企业高管": "总经理 老板 管理层 审批",
    "29-自由职业": "自由职业 接单 一人公司",
    "30-家庭共享": "家里人一起用 全家共用 家庭换电脑",
}

NOTE_MARKS = ("删掉", "删除", "去掉", "不要写", "不要", "别写", "不写", "只保留", "只写", "改成", "突出", "弱化")
PRODUCT_MIN = 0.18
PRODUCT_MARGIN = 0.08
SLOT_MIN = 0.42
SLOT_MARGIN = 0.06
AUDIENCE_MIN = 0.22
AUDIENCE_MARGIN = 0.08

_INDEXES: dict = {}


class VectorIndex:
    """字片段 TF-IDF 向量，用余弦相似度排序。"""

    def __init__(self, docs: list[tuple[str, str]]):
        self.ids = [doc_id for doc_id, _ in docs]
        counts = [_ngrams(text) for _, text in docs]
        df = Counter()
        for count in counts:
            df.update(count.keys())
        total = len(docs) or 1
        self.idf = {gram: math.log((1 + total) / (1 + freq)) + 1 for gram, freq in df.items()}
        self.vectors = [self._weight(count) for count in counts]
        self.norms = [_norm_of(vector) for vector in self.vectors]

    def _weight(self, count: Counter) -> dict:
        total = sum(count.values()) or 1
        return {gram: (freq / total) * self.idf.get(gram, 1.0) for gram, freq in count.items()}

    def rank(self, text: str) -> list[tuple[str, float]]:
        query = self._weight(_ngrams(text))
        query_norm = _norm_of(query)
        if not query or query_norm == 0:
            return []
        scored = []
        for doc_id, vector, norm in zip(self.ids, self.vectors, self.norms):
            if norm == 0:
                scored.append((doc_id, 0.0))
                continue
            dot = sum(value * vector[gram] for gram, value in query.items() if gram in vector)
            scored.append((doc_id, dot / (query_norm * norm)))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored


def map_sentence(sentence: str) -> dict:
    """返回型号、人群、场景、平台和从句子里拆出的临时要求。对不上的项留空。"""
    body, note = _split_note(sentence or "")
    product = _match_product(body)
    audience = _match_audience(body)
    scene = _match_labeled(body, _scene_catalog(), "scene", SLOT_MIN, SLOT_MARGIN)
    platform = _match_labeled(body, _platform_catalog(), "platform", SLOT_MIN, SLOT_MARGIN)
    return {
        "product": product,
        "audience": audience,
        "scene": scene,
        "platform": platform,
        "note": note,
    }


def apply_sentence(product: str, audience: str, scene: str, platform: str, note: str, brief: str) -> dict:
    """一句话补全留空项。型号和人群以手填为准；句子里点名的场景和平台覆盖下拉框。"""
    product = (product or "").strip()
    audience = (audience or "").strip()
    note = (note or "").strip()
    brief = (brief or "").strip()
    scene = scene or ""
    platform = platform or ""
    if not brief:
        return {
            "product": product,
            "audience": audience,
            "scene": scene,
            "platform": platform,
            "note": note,
            "detail": "",
        }
    mapped = map_sentence(brief)
    return {
        "product": product or mapped["product"],
        "audience": audience or mapped["audience"],
        "scene": mapped["scene"] or scene,
        "platform": mapped["platform"] or platform,
        "note": note or mapped["note"],
        "detail": _detail(mapped, bool(product), bool(audience), bool(note)),
    }


def _detail(mapped: dict, keep_product: bool, keep_audience: bool, keep_note: bool) -> str:
    parts = [
        f"型号 {mapped['product'] or '未确定'}",
        f"人群 {mapped['audience'] or '未确定'}",
        f"场景 {mapped['scene'] or '沿用下拉框'}",
        f"平台 {mapped['platform'] or '沿用下拉框'}",
    ]
    text = "文本向量映射：" + "；".join(parts) + "。"
    if mapped["note"] and not keep_note:
        text += f"临时要求：{mapped['note']}。"
    if keep_product:
        text += "型号以手填为准。"
    if keep_audience:
        text += "人群以手填为准。"
    return text


def _split_note(sentence: str) -> tuple[str, str]:
    parts = re.split(r"[，,；;。！？\n]", sentence)
    notes = []
    body = []
    for part in parts:
        text = part.strip()
        if not text:
            continue
        if any(mark in text for mark in NOTE_MARKS):
            notes.append(text)
        else:
            body.append(text)
    return "，".join(body) or sentence.strip(), "，".join(notes)


def _match_product(text: str) -> str:
    exact = _exact_product(text)
    if exact:
        return exact
    return _best(_indexes()["product"].rank(text), PRODUCT_MIN, PRODUCT_MARGIN)


def _exact_product(text: str) -> str:
    hits = []
    for canonical, aliases, _descriptor in PRODUCTS:
        for alias in aliases:
            if classify_title(alias, text) != "exact":
                continue
            hits.append((canonical, _norm(alias)))
    return _choose_canonical(_drop_shorter_prefixes(hits))


def _match_audience(text: str) -> str:
    ranked = sorted(
        (
            (sum(len(word) for word in module["keywords"] if _contains(text, word)), module_id)
            for module_id, module in MODULES.items()
        ),
        reverse=True,
    )
    best_score, best_id = ranked[0]
    second_score = ranked[1][0]
    if best_score > 0 and best_score - second_score >= 2:
        words = [word for word in MODULES[best_id]["keywords"] if _contains(text, word)]
        return " ".join(words)
    chosen = _best(_indexes()["audience"].rank(text), AUDIENCE_MIN, AUDIENCE_MARGIN)
    if not chosen:
        return ""
    module = MODULES[chosen]
    return module["name"] + " " + " ".join(module["keywords"])


def _match_labeled(text: str, catalog: list[tuple[str, list[str]]], index_name: str, minimum: float, margin: float) -> str:
    exact = _exact_label(text, catalog)
    if exact:
        return exact
    return _best(_indexes()[index_name].rank(text), minimum, margin)


def _exact_label(text: str, catalog: list[tuple[str, list[str]]]) -> str:
    sentence = _norm(text)
    hits = []
    for canonical, aliases in catalog:
        for alias in aliases:
            alias_n = _norm(alias)
            if alias_n and alias_n in sentence:
                hits.append((canonical, alias_n))
    return _choose_canonical(_drop_shorter_prefixes(hits))


def _choose_canonical(hits: list[tuple[str, str]]) -> str:
    if not hits:
        return ""
    longest = max(len(alias_n) for _canonical, alias_n in hits)
    canonicals = list(dict.fromkeys(canonical for canonical, alias_n in hits if len(alias_n) == longest))
    if len(canonicals) == 1:
        return canonicals[0]
    return ""


def _drop_shorter_prefixes(hits: list[tuple[str, str]]) -> list[tuple[str, str]]:
    kept = []
    for canonical, alias_n in hits:
        shadowed = any(
            other_n != alias_n and other_n.startswith(alias_n) and len(other_n) > len(alias_n)
            for _other_id, other_n in hits
        )
        if not shadowed:
            kept.append((canonical, alias_n))
    return kept


def _best(ranked: list[tuple[str, float]], minimum: float, margin: float) -> str:
    if not ranked:
        return ""
    top_id, top_score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    if top_score >= minimum and top_score - second >= margin:
        return top_id
    return ""


def _contains(text: str, word: str) -> bool:
    if word in text:
        return True
    return word.lower() in text.lower()


def _ngrams(text: str) -> Counter:
    compact = _norm(text)
    grams: Counter = Counter()
    if not compact:
        return grams
    if len(compact) < 2:
        grams[compact] += 1
        return grams
    for size in (2, 3):
        if len(compact) < size:
            continue
        for index in range(len(compact) - size + 1):
            grams[compact[index : index + size]] += 1
    return grams


def _norm_of(vector: dict) -> float:
    if not vector:
        return 0.0
    return math.sqrt(sum(value * value for value in vector.values()))


def _indexes() -> dict:
    if _INDEXES:
        return _INDEXES
    _INDEXES["product"] = VectorIndex([(name, f"{name} {' '.join(aliases)} {descriptor}") for name, aliases, descriptor in PRODUCTS])
    _INDEXES["audience"] = VectorIndex(
        [
            (module_id, f"{module['name']} {module['brief']} {' '.join(module['keywords'])} {AUDIENCE_HINTS.get(module_id, '')}")
            for module_id, module in MODULES.items()
        ]
    )
    _INDEXES["scene"] = VectorIndex([(scene, f"{scene} {' '.join(SCENE_ALIASES.get(scene, []))}") for scene in MARKETING_SCENES])
    _INDEXES["platform"] = VectorIndex([(name, f"{name} {' '.join(PLATFORM_ALIASES.get(name, [name]))}") for name in PLATFORMS])
    return _INDEXES


def _scene_catalog() -> list[tuple[str, list[str]]]:
    return [(scene, SCENE_ALIASES.get(scene, [scene])) for scene in MARKETING_SCENES]


def _platform_catalog() -> list[tuple[str, list[str]]]:
    return [(name, PLATFORM_ALIASES.get(name, [name])) for name in PLATFORMS]
