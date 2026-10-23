"""把用户的人群映射到一个行业模块（用来取该模块的客户画像）。

映射得上就用对应画像；映射不上就走通用，让模型按自己对人群的理解来写，不再追问。
"""

from scenario_catalog import MODULES


def generic_route() -> dict:
    """人群/场景无明确或没对上画像时的通用路由：不绑定行业画像。"""
    return {
        "status": "matched",
        "generic": True,
        "module_id": "",
        "module_name": "",
        "module_brief": "通用产品软文（无特定行业画像）",
        "children": [],
        "questions": [],
    }


def resolve_scenario(audience: str, scene: str, note: str = "") -> dict:
    text = f"{audience} {note}"
    ranked = sorted(
        ((sum(len(word) for word in MODULES[module_id]["keywords"] if word in text), module_id) for module_id in MODULES),
        reverse=True,
    )
    best_score, best_id = ranked[0]
    if best_score == 0:
        return generic_route()
    module = MODULES[best_id]
    return {
        "status": "matched",
        "generic": False,
        "module_id": best_id,
        "module_name": module["name"],
        "module_brief": module["brief"],
        "children": [],
        "questions": [],
    }
