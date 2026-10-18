from scenario_router import resolve_scenario
from strategy import classify_title, missing_questions
from compliance import check_text
from vector_map import apply_sentence, map_sentence


def test_missing_questions():
    questions = missing_questions("", "", "开学季", "小红书")
    assert any("型号" in item for item in questions)
    assert any("写给谁" in item for item in questions)
    assert missing_questions("MateBook D 14", "大学新生", "开学季", "小红书") == []


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


def test_scenario_maps_education_admin_to_parent_and_module():
    route = resolve_scenario("学校教务和信息中心", "开学季", "")
    assert route["status"] == "matched"
    assert route["parent_title"] == "教育场景问题"
    assert route["module_id"] == "06-教育管理"
    assert [item["role"] for item in route["children"]] == ["客户画像", "问题清单", "方案输出模板", "验收清单", "完整参考案例"]


def test_student_maps_to_college_module_under_same_parent():
    route = resolve_scenario("准备开学的大学新生", "开学季", "")
    assert route["module_id"] == "08-高校学生"
    assert route["parent_title"] == "教育场景问题"


def test_vague_office_user_must_choose_module():
    route = resolve_scenario("经常出差的商务人士", "职场办公", "")
    assert route["status"] == "ambiguous"
    assert any("移动办公场景卡" in item for item in route["questions"])


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
    assert any(item["role"] == "母文档" and "教育" in item["text"] for item in pack["scenario_docs"])
    assert any(item["role"] == "客户画像" and item["text"] for item in pack["scenario_docs"])
    assert any(item["role"] == "方案输出模板" and item["text"] for item in pack["scenario_docs"])
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


def test_sentence_maps_education_admin_wechat():
    mapped = map_sentence("给学校教务和信息中心写一篇 MateBook D 14 开学季微信公众号，删掉续航，只保留携带")
    assert mapped["product"] == "MateBook D 14"
    assert mapped["scene"] == "开学季"
    assert mapped["platform"] == "微信公众号"
    assert mapped["note"] == "删掉续航，只保留携带"
    route = resolve_scenario(mapped["audience"], mapped["scene"], mapped["note"])
    assert route["status"] == "matched"
    assert route["module_id"] == "06-教育管理"


def test_sentence_maps_freshman_redbook_without_other_fields():
    mapped = map_sentence("给准备开学的大学新生写一篇 MateBook D 14 的小红书，删掉续航，只保留携带")
    assert mapped["product"] == "MateBook D 14"
    assert mapped["scene"] == "开学季"
    assert mapped["platform"] == "小红书"
    assert "只保留携带" in mapped["note"]
    route = resolve_scenario(mapped["audience"], mapped["scene"], "")
    assert route["module_id"] == "08-高校学生"


def test_nearby_models_stay_distinct_in_vector_map():
    assert map_sentence("写 MateBook D 16 的公众号")["product"] == "MateBook D 16"
    assert map_sentence("MateBook D 16 SE 版 门店海报")["product"] == "MateBook D 16 SE 版"
    assert map_sentence("鸿蒙 MateBook 14 开学")["product"] == "HUAWEI MateBook 14"
    assert map_sentence("MateBook Pro S 的知乎")["product"] == "HUAWEI MateBook Pro S"
    assert map_sentence("对比 MateBook D 14 和 MateBook D 16 怎么选")["product"] == ""


def test_unspecified_model_is_not_guessed():
    mapped = map_sentence("给大学新生写一篇开学季小红书")
    assert mapped["product"] == ""
    assert mapped["platform"] == "小红书"
    assert mapped["scene"] == "开学季"
    assert map_sentence("帮我写一篇 MateBook 的小红书")["product"] == ""


def test_vector_maps_paraphrase_without_catalog_keyword():
    mapped = map_sentence("给画海报的视觉同学写一篇小红书")
    route = resolve_scenario(mapped["audience"], "内容创作", "")
    assert route["module_id"] == "13-设计创意"
    assert mapped["platform"] == "小红书"
    assert mapped["product"] == ""


def test_vector_maps_entry_laptop_phrase_to_d14():
    mapped = map_sentence("写一台入门轻薄本的开学季公众号")
    assert mapped["product"] == "MateBook D 14"
    assert mapped["scene"] == "开学季"
    assert mapped["platform"] == "微信公众号"


def test_hand_filled_model_and_audience_win_over_sentence():
    resolved = apply_sentence(
        "MateBook D 16",
        "大学新生",
        "开学季",
        "小红书",
        "只保留接口",
        "给学校教务写 MateBook D 14 微信公众号，删掉续航",
    )
    assert resolved["product"] == "MateBook D 16"
    assert resolved["audience"] == "大学新生"
    assert resolved["platform"] == "微信公众号"
    assert resolved["note"] == "只保留接口"
    assert "型号以手填为准" in resolved["detail"]


def test_empty_sentence_keeps_the_form():
    resolved = apply_sentence("MateBook D 14", "大学新生", "开学季", "小红书", "", "")
    assert resolved["product"] == "MateBook D 14"
    assert resolved["audience"] == "大学新生"
    assert resolved["scene"] == "开学季"
    assert resolved["platform"] == "小红书"
    assert resolved["detail"] == ""


if __name__ == "__main__":
    test_missing_questions()
    test_nearby_model_is_not_exact()
    test_compliance_flags_price_and_absolute_words()
    test_scenario_maps_education_admin_to_parent_and_module()
    test_student_maps_to_college_module_under_same_parent()
    test_vague_office_user_must_choose_module()
    test_article_render_embeds_cached_image()
    test_platform_points_at_p6_template()
    test_local_kb_feeds_editor_slots()
    test_sentence_maps_education_admin_wechat()
    test_sentence_maps_freshman_redbook_without_other_fields()
    test_nearby_models_stay_distinct_in_vector_map()
    test_unspecified_model_is_not_guessed()
    test_vector_maps_paraphrase_without_catalog_keyword()
    test_vector_maps_entry_laptop_phrase_to_d14()
    test_hand_filled_model_and_audience_win_over_sentence()
    test_empty_sentence_keeps_the_form()
    print("core checks passed")
