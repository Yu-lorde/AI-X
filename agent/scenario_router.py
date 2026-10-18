"""把用户的人群和场景映射到 P8 母文档，再映射到其中的一个行业模块。"""

from scenario_catalog import CHILD_ROLES, MODULES, PARENTS


def resolve_scenario(audience: str, scene: str, note: str = "") -> dict:
    text = f"{audience} {note}"
    ranked = sorted(
        ((sum(len(word) for word in MODULES[module_id]["keywords"] if word in text), module_id) for module_id in MODULES),
        reverse=True,
    )
    best_score, best_id = ranked[0]
    second_score = ranked[1][0]
    if best_score == 0 or best_score - second_score < 2:
        parent = _parent_for_scene(scene)
        options = [_label(module_id) for module_id in parent["modules"]]
        return {
            "status": "ambiguous",
            "questions": [
                f"当前场景对应 P8 母文档《{parent['title']}》，但人群还不能唯一对应下面的行业模块。请在补充说明里写明模块名称：",
                *options,
            ],
        }

    parent = _parent_for_module(best_id, scene)
    module = MODULES[best_id]
    return {
        "status": "matched",
        "parent_id": parent["id"],
        "parent_title": parent["title"],
        "module_id": best_id,
        "module_name": module["name"],
        "module_brief": module["brief"],
        "children": [
            {"role": role, "use": use, "query": f"{module['name']} {role}"}
            for role, use in CHILD_ROLES
        ],
        "questions": [],
    }


def _parent_for_scene(scene: str) -> dict:
    for parent in PARENTS:
        if scene in parent["scenes"]:
            return parent
    return PARENTS[0]


def _parent_for_module(module_id: str, scene: str) -> dict:
    owners = [parent for parent in PARENTS if module_id in parent["modules"]]
    if not owners:
        module = MODULES[module_id]
        return {"id": module_id, "title": module["name"], "scenes": [], "modules": [module_id]}
    for parent in owners:
        if scene in parent["scenes"]:
            return parent
    return owners[0]


def _label(module_id: str) -> str:
    module = MODULES[module_id]
    return f"{module_id}：{module['brief']}"
