from scenario_router import resolve_scenario
from strategy import classify_title, missing_questions
from compliance import check_text


def test_missing_questions():
    # 型号和平台必填；人群、场景可留空（留空走通用软文）。
    questions = missing_questions("", "大学新生", "开学季", "")
    assert any("型号" in item for item in questions)
    assert any("发布平台" in item for item in questions)
    assert missing_questions("MateBook D 14", "大学新生", "开学季", "小红书") == []
    # 人群留空、场景选无明确，不再追问，直接放行。
    assert missing_questions("MateBook D 14", "", "无明确", "小红书") == []


def test_nearby_model_is_not_exact():
    assert classify_title("MateBook D 16", "MateBook D 16 SE 版") == "nearby"
    assert classify_title("MateBook D 14", "HUAWEI MateBook D 14 产品事实") == "exact"
    assert classify_title("MateBook 14", "MateBook D 14") == "no"
    assert classify_title("MateBook D 14", "hwpc_matebook-d-14-2024_高清护眼屏幕_06.png") == "exact"


def test_compliance_flags_price_and_absolute_words():
    issues = check_text("这是最强轻薄本，只要3999元。", "重量约1.4kg", "公众号")
    assert any("最强" in item for item in issues)
    assert any("3999" in item for item in issues)
    assert check_text("适合出差开会。", "适合出差开会。", "公众号") == []


def test_compliance_flags_leaked_specs_not_in_p1():
    # P1 是 D14：1920×1200、300尼特、56Wh、1.39kg。范文里的 2.8K/70Wh/120Hz 搬进来应被判无依据。
    source = "屏幕 14 英寸 1920×1200 300 尼特 100% sRGB 电池 56 Wh 重量约 1.39 kg"
    out = "这块 2.8K OLED 屏，120Hz 高刷，70Wh 大电池，拎着才 1.39kg。"
    issues = check_text(out, source, "小红书")
    assert any("2.8K" in item for item in issues)
    assert any("70Wh" in item for item in issues)
    assert any("120Hz" in item for item in issues)
    # 1.39kg、300尼特、56Wh 这些 P1 里有的数字不应被误判
    ok = check_text("重量 1.39kg，300尼特，56Wh，14英寸。", source, "小红书")
    assert ok == []


def test_compliance_flags_first_person_fabricated_experience():
    # 录屏里的小红书标题/导语：第一人称购买与使用经历必须被拦。
    title = "大学生活效率翻倍!我的 MateBook D 14 使用体验"
    lead = "作为一名大二学生,每天在宿舍、教室和图书馆之间奔波,最近入手了 HUAWEI MateBook D 14,分享一下我的使用体验~"
    issues = check_text(f"{title}\n{lead}", "产品事实", "小红书")
    joined = " ".join(issues)
    assert "虚构" in joined and "我" in joined
    # 场景视角、第三人称不误伤
    safe = "新生选笔记本，先看课程、携带与续航需求。每天在教室、图书馆和宿舍之间来回，背包里的东西越轻越好。"
    assert check_text(safe, "产品事实", "小红书") == []
    # 其他平台维持原规则
    assert check_text(lead, "产品事实", "公众号") == []


def test_scenario_maps_education_admin_to_module():
    # 人群映射到行业模块（用来取该模块的客户画像），不再有母文档/五份文档/追问。
    route = resolve_scenario("学校教务和信息中心", "开学季", "")
    assert route["status"] == "matched"
    assert route["generic"] is False
    assert route["module_id"] == "06-教育管理"


def test_student_maps_to_college_module():
    route = resolve_scenario("准备开学的大学新生", "开学季", "")
    assert route["module_id"] == "08-高校学生"


def test_unknown_audience_falls_back_to_generic_not_ambiguous():
    # 人群没对上任何模块 → 通用（模型按理解写），不再追问。
    route = resolve_scenario("某种很小众说不清的人群", "职场办公", "")
    assert route["status"] == "matched"
    assert route["generic"] is True


def test_article_render_embeds_cached_image(tmp_path=None):
    from pathlib import Path
    import tempfile
    from render import render_result

    folder = Path(tempfile.mkdtemp())
    image = folder / "screen.png"
    image.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\xef\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    result = {
        "ok": True,
        "strategy": {
            "audience": "大学新生",
            "scene": "开学季",
            "module_brief": "携带和续航",
            "platform": "小红书",
            "parent_title": "教育场景问题",
            "template_query": "小红书图文创作指南",
            "product": "MateBook D 14",
        },
        "documents": [{"title": "MateBook D 14 产品事实"}],
        "article": {
            "title": "开学带这台",
            "title_options": ["开学带这台"],
            "lead": "先看重量。",
            "paragraphs": ["上课和搬家都要拎得动。"],
            "cta": "到店核对具体配置。",
            "tags": ["开学"],
            "facts": [{"point": "定位为入门轻薄本", "source_title": "MateBook D 14 产品事实"}],
            "images": [
                {
                    "name": "hwpc_matebook-d-14-2024_高清护眼屏幕_06.png",
                    "source": "hwpc_matebook-d-14-2024_高清护眼屏幕_06.png",
                    "position": "第1段之后",
                    "caption": "高清护眼屏幕",
                    "path": str(image),
                    "theme": "高清护眼屏幕",
                }
            ],
        },
        "verification": {"facts": ["通过"], "images": ["通过"], "compliance": ["通过"], "pending": ["无"]},
    }
    page = render_result(result)
    assert "一、场景判断" in page and "三、图文软文" in page
    assert "data:image/png;base64," in page
    assert "高清护眼屏幕" in page


def test_platform_points_at_p6_template():
    from strategy import platform_rules

    wechat = platform_rules("公众号")
    assert wechat["platform"] == "微信公众号"
    assert wechat["template_query"] == "微信公众号长图文创作指南"
    assert wechat["template_file"] == "微信公众号图文模板"
    redbook = platform_rules("小红书")
    assert redbook["template_query"] == "小红书图文创作指南"
    assert "structure" not in redbook


def test_local_kb_feeds_editor_slots():
    from pathlib import Path

    from editor import compose_article, pack_state, slot_names
    from local_kb import collect
    from render import render_checks, render_effect, render_sources
    from strategy import platform_rules

    route = resolve_scenario("学校教务和信息中心", "开学季", "")
    strategy = {"product": "MateBook D 14", **platform_rules("公众号"), **route}
    pack = collect(route, strategy)
    # 场景只保留客户画像
    assert [item["role"] for item in pack["scenario_docs"]] == ["客户画像"]
    assert pack["scenario_docs"][0]["text"]
    assert "公众号" in pack["platform_doc"]["title"] and pack["platform_doc"]["text"]
    assert pack["documents"] and "产品事实" in pack["documents"][0]["title"]
    assert pack["images"] and Path(pack["images"][0]["path"]).is_file()

    article = {
        "title": "教务办公怎么选",
        "title_options": ["教务办公怎么选", "开学前先核对配置"],
        "lead": "先看已确认的规格。",
        "paragraphs": ["第一段说明携带。", "第二段说明接口。"],
        "cta": "到店核对具体配置。",
        "tags": [],
        "facts": [{"point": "定位为入门轻薄本", "source_title": pack["documents"][0]["title"]}],
        "images": [
            {"name": pack["images"][0]["title"], "position": "封面", "caption": pack["images"][0]["theme"]},
            {"name": pack["images"][1]["title"], "position": "第2段之后", "caption": "接口画面"},
        ],
    }
    result = {
        "article": article,
        "images": pack["images"],
        "documents": pack["documents"],
        "scenario_docs": pack["scenario_docs"],
        "platform_doc": pack["platform_doc"],
        "strategy": strategy,
        "source": pack["source"],
        "verification": {"facts": ["通过"], "images": ["通过"], "compliance": ["通过"], "pending": ["无"]},
    }
    state = pack_state(result)
    names = slot_names({**article, "paragraphs": state["paragraphs"]}, state["paragraph_count"])
    assert names[0] == pack["images"][0]["title"]
    assert names[2] == pack["images"][1]["title"]
    edited = compose_article(
        "改后的标题",
        "备选一\n备选二",
        article["lead"],
        state["paragraphs"],
        article["cta"],
        "",
        names,
        ["封面说明", "", "第二段配图"],
        state,
    )
    page = render_effect(edited, "微信公众号")
    assert page.index("改后的标题") < page.index("第一段说明携带")
    assert "/gradio_api/file=" in page
    assert "第二段配图" in page
    sources = render_sources(strategy, edited, pack["documents"], pack["scenario_docs"], pack["source"])
    checks = render_checks(result["verification"])
    assert "二、知识库依据" in sources and "产品型号" in sources and "MateBook D 14" in sources
    assert "四、核验结果" in checks and "产品事实" in checks and "待确认信息" in checks


if __name__ == "__main__":
    test_missing_questions()
    test_nearby_model_is_not_exact()
    test_compliance_flags_price_and_absolute_words()
    test_compliance_flags_leaked_specs_not_in_p1()
    test_compliance_flags_first_person_fabricated_experience()
    test_scenario_maps_education_admin_to_module()
    test_student_maps_to_college_module()
    test_unknown_audience_falls_back_to_generic_not_ambiguous()
    test_article_render_embeds_cached_image()
    test_platform_points_at_p6_template()
    test_local_kb_feeds_editor_slots()
    print("core checks passed")
