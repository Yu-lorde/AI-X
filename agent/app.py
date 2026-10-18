import gradio as gr

from config import DEFAULT_KB_NAME, ROOT, credential_status, env, load_env_file
from editor import MAX_PARAS, NONE, caption_for, compose_article, intro_line, live_verification, pack_state, slot_names
from ima_client import ImaError, probe_connection
from local_kb import KB_ROOT
from pipeline import _export, run
from render import render_checks, render_effect, render_sources
from strategy import MARKETING_SCENES, PLATFORMS
from vector_map import apply_sentence

PAGE_CSS = """
.copy-section { margin: 0 0 16px; padding: 18px 22px; border: 1px solid var(--border-color-primary); border-radius: 14px; background: var(--block-background-fill); }
.copy-section h2 { margin: 0 0 12px; font-size: 18px; }
.copy-section h3 { margin: 8px 0 10px; font-size: 22px; line-height: 1.4; }
.copy-section p { margin: 0 0 10px; line-height: 1.75; }
.copy-section .lead { font-size: 16px; }
.copy-section .scene-line { opacity: .75; font-size: 13px; }
.copy-section .label { margin: 12px 0 4px; font-weight: 600; }
.copy-section ul { margin: 0 0 8px 18px; padding: 0; }
.copy-section li span { display: block; opacity: .72; font-size: 13px; }
.copy-section figure { margin: 12px 0 16px; }
.copy-section img { width: 100%; max-height: 460px; object-fit: contain; border-radius: 10px; display: block; background: #f4f4f4; }
.copy-section figcaption { margin-top: 6px; font-size: 13px; line-height: 1.5; opacity: .8; }
.copy-section figcaption span { display: block; }
.copy-section .cta, .copy-section .tags, .copy-section .options { opacity: .9; }
.effect-sheet { min-height: 480px; }
.effect-col { position: sticky; top: 12px; align-self: flex-start; }
"""


def _status_text() -> str:
    load_env_file()
    status = credential_status()
    ima = "已检测到" if status["ima_id"] and status["ima_key"] else "未检测到，将改用本地知识库"
    llm = "已检测到" if status["llm_key"] else "未检测到"
    return f"ima 凭证：{ima}。大模型密钥：{llm}。页面不显示密钥。"


def test_connection():
    load_env_file()
    status = credential_status()
    if not (status["ima_id"] and status["ima_key"]):
        report = "### 未连接远程知识库\n\n没有检测到 ima 凭证。生成时会改读本地「华为PC知识库」。"
        return report, _status_text()
    try:
        report = probe_connection(env("IMA_KB_NAME", DEFAULT_KB_NAME))
    except ImaError as exc:
        report = f"### 连接失败\n\n{exc}\n\n生成时会改读本地知识库。"
    return report, _status_text()


def _notice(result: dict) -> str:
    parts = [result.get("message") or "", result.get("detail") or ""]
    parts.extend(result.get("questions") or [])
    return "；".join(part for part in parts if part)


def _gallery_value(state: dict):
    return [(item["path"], item["theme"] or item["name"]) for item in state.get("candidates") or []]


def _focus_choices(count: int) -> list[str]:
    return ["封面"] + [f"第{index}段后" for index in range(1, count + 1)]


def _idle_fields():
    fields = [gr.update(value="", visible=True) for _ in range(4)]
    fields.append(gr.update(value="", visible=False))
    fields.append(gr.update(choices=[NONE], value=NONE, visible=True))
    fields.append(gr.update(value="", visible=True))
    fields.append(gr.update(choices=["封面"], value="封面"))
    fields.append(gr.update(value=[]))
    fields.extend(gr.update(visible=False) for _ in range(MAX_PARAS))
    fields.extend(gr.update(value="", visible=False) for _ in range(MAX_PARAS))
    fields.extend(gr.update(choices=[NONE], value=NONE, visible=False) for _ in range(MAX_PARAS))
    fields.extend(gr.update(value="", visible=False) for _ in range(MAX_PARAS))
    return fields


def _preview(title, options, lead, cta, tags, cover, cover_cap, paragraphs, picks, captions, state):
    count = state.get("paragraph_count") or 1
    article = compose_article(
        title,
        options,
        lead,
        list(paragraphs)[:count],
        cta,
        tags,
        [cover, *picks][: count + 1],
        [cover_cap, *captions][: count + 1],
        state,
    )
    verification = live_verification(state, article)
    export = _export(
        state.get("strategy") or {},
        state.get("scenario_docs") or [],
        state.get("platform_doc") or {},
        state.get("documents") or [],
        article,
        verification,
    )
    return render_effect(article, intro_line(state)), render_checks(verification), export


def refresh(title, options, lead, cta, tags, cover, cover_cap, p1, p2, p3, p4, p5, p6, i1, i2, i3, i4, i5, i6, c1, c2, c3, c4, c5, c6, state):
    if not state or not state.get("ready"):
        return gr.update(), gr.update(), gr.update()
    return _preview(
        title,
        options,
        lead,
        cta,
        tags,
        cover,
        cover_cap,
        [p1, p2, p3, p4, p5, p6],
        [i1, i2, i3, i4, i5, i6],
        [c1, c2, c3, c4, c5, c6],
        state,
    )


def on_pick(focus, state, evt: gr.SelectData):
    updates = [gr.update() for _ in range(2 + MAX_PARAS * 2)]
    candidates = (state or {}).get("candidates") or []
    index = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
    if not state or not state.get("ready") or index is None or not (0 <= int(index) < len(candidates)):
        return updates
    name = candidates[int(index)]["name"]
    labels = _focus_choices(state.get("paragraph_count") or 1)
    if focus not in labels:
        return updates
    slot = labels.index(focus)
    updates[slot] = gr.update(value=name)
    updates[1 + MAX_PARAS + slot] = gr.update(value=caption_for(name, state))
    return updates


def _form_updates(brief, product, audience, scene, platform, note):
    if not (brief or "").strip():
        return [gr.update() for _ in range(5)]
    return [
        gr.update(value=product),
        gr.update(value=audience),
        gr.update(value=scene),
        gr.update(value=platform),
        gr.update(value=note),
    ]


def generate(product, audience, scene, platform, note, brief):
    resolved = apply_sentence(product, audience, scene, platform, note, brief)
    product = resolved["product"]
    audience = resolved["audience"]
    scene = resolved["scene"]
    platform = resolved["platform"]
    note = resolved["note"]
    form = _form_updates(brief, product, audience, scene, platform, note)
    result = run(product or "", audience or "", scene or "", platform or "", note or "")
    status = _status_text()
    if resolved.get("detail"):
        status += "\n\n" + resolved["detail"]
    if result.get("message"):
        status += "\n\n" + result["message"]
    export = result.get("export_text") or ""
    if not result.get("ok"):
        return [
            render_effect(None, notice=_notice(result)),
            render_sources(result.get("strategy"), None, result.get("documents"), result.get("scenario_docs"), result.get("source") or ""),
            render_checks(None),
            {},
            status,
            export,
            *_idle_fields(),
            *form,
        ]
    state = pack_state(result)
    article = result["article"]
    paragraphs = state["paragraphs"]
    count = len(paragraphs)
    names = slot_names({**article, "paragraphs": paragraphs}, count)
    caps = [caption_for(name, state) for name in names]
    choices = [NONE] + [item["name"] for item in state["candidates"]]
    options = "\n".join(article.get("title_options") or [])
    tag_text = " ".join(article.get("tags") or [])
    effect, checks, export = _preview(
        article.get("title") or "",
        options,
        article.get("lead") or "",
        article.get("cta") or "",
        tag_text,
        names[0],
        caps[0],
        paragraphs,
        names[1:],
        caps[1:],
        state,
    )
    fields = [
        gr.update(value=article.get("title") or "", visible=True),
        gr.update(value=options, visible=True),
        gr.update(value=article.get("lead") or "", visible=True),
        gr.update(value=article.get("cta") or "", visible=True),
        gr.update(value=tag_text, visible=state["use_tags"]),
        gr.update(choices=choices, value=names[0], visible=True),
        gr.update(value=caps[0], visible=True),
        gr.update(choices=_focus_choices(count), value="封面"),
        gr.update(value=_gallery_value(state)),
    ]
    fields.extend(gr.update(visible=index < count) for index in range(MAX_PARAS))
    fields.extend(gr.update(value=paragraphs[index] if index < count else "", visible=index < count) for index in range(MAX_PARAS))
    fields.extend(
        gr.update(choices=choices, value=names[index + 1] if index < count else NONE, visible=index < count)
        for index in range(MAX_PARAS)
    )
    fields.extend(gr.update(value=caps[index + 1] if index < count else "", visible=index < count) for index in range(MAX_PARAS))
    return [
        effect,
        render_sources(state["strategy"], {"facts": state["facts"]}, state["documents"], state["scenario_docs"], state["source"]),
        checks,
        state,
        status,
        export,
        *fields,
        *form,
    ]


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="华为PC营销软文智能体") as demo:
        gr.Markdown(
            """# 华为 PC 营销软文智能体
上方填写任务，也可以只写一句话。一句话会按文本向量映射到型号、人群、场景和平台。中间是图文：左边看效果，右边按位置改文字，配图可以从备选图片里重选。页面最下方分开显示知识库依据和核验结果。远程知识库不可用时，自动改读本地华为 PC 知识库。"""
        )
        with gr.Row():
            status = gr.Markdown(_status_text())
            test_button = gr.Button("测试共享知识库", scale=0)
        with gr.Group():
            brief = gr.Textbox(
                label="一句话需求（可选）",
                info="只填这一句也可以生成。句子会映射到型号、人群、场景和平台；没点名的场景和平台沿用下拉框。型号和人群如果已经手填，以手填为准。",
                placeholder="例如 给学校教务和信息中心写 MateBook D 14 开学季微信公众号，删掉续航只保留携带",
                lines=1,
            )
            with gr.Row():
                product = gr.Textbox(label="产品型号", placeholder="例如 MateBook D 14", lines=1, max_lines=1, scale=1)
                audience = gr.Textbox(label="目标人群", placeholder="例如 大学新生", lines=1, max_lines=1, scale=1)
                scene = gr.Dropdown(choices=MARKETING_SCENES, label="业务场景", value="开学季", scale=1)
                platform = gr.Dropdown(choices=list(PLATFORMS), label="发布平台", value="小红书", scale=1)
            with gr.Row():
                note = gr.Textbox(label="临时修改要求", placeholder="例如 删掉续航，只保留携带", lines=1, scale=4)
                button = gr.Button("生成并核验", variant="primary", scale=1)
        gr.Examples(
            examples=[
                ["MateBook D 14", "学校教务和信息中心", "开学季", "微信公众号", "", ""],
                ["MateBook D 14", "准备开学的大学新生", "开学季", "小红书", "", ""],
                ["", "", "开学季", "小红书", "", "给准备开学的大学新生写一篇 MateBook D 14 的小红书，删掉续航，只保留携带"],
            ],
            inputs=[product, audience, scene, platform, note, brief],
        )
        editor_state = gr.State({})
        with gr.Row(elem_classes=["work-row"]):
            with gr.Column(elem_classes=["effect-col"], scale=3):
                effect = gr.HTML(render_effect(None))
            with gr.Column(scale=2):
                gr.Markdown("### 编辑区")
                title = gr.Textbox(label="标题", lines=2)
                options = gr.Textbox(label="标题备选（一行一个）", lines=3)
                lead = gr.Textbox(label="导语", lines=3)
                cover = gr.Dropdown(label="封面图：从备选图片重选", choices=[NONE], value=NONE)
                cover_cap = gr.Textbox(label="封面图说明", lines=2)
                groups = []
                paras = []
                picks = []
                caps = []
                for index in range(MAX_PARAS):
                    with gr.Group(visible=False) as group:
                        paras.append(gr.Textbox(label=f"第{index + 1}段", lines=4))
                        picks.append(gr.Dropdown(label=f"第{index + 1}段后的配图：从备选图片重选", choices=[NONE], value=NONE))
                        caps.append(gr.Textbox(label=f"第{index + 1}段配图说明", lines=2))
                    groups.append(group)
                cta = gr.Textbox(label="行动引导", lines=2)
                tags = gr.Textbox(label="标签", lines=1, visible=False)
                focus = gr.Radio(choices=["封面"], value="封面", label="要替换的配图位置")
                gallery = gr.Gallery(
                    label="备选图片。先选定位置，再点击一张图片替换",
                    columns=3,
                    height=280,
                    allow_preview=False,
                    object_fit="contain",
                )
        with gr.Accordion("连接详情与导出文本", open=False):
            connection = gr.Markdown("需要核对共享库时，点上方「测试共享知识库」。")
            export_box = gr.Textbox(label="导出文本", lines=16)
        with gr.Row():
            sources = gr.HTML(render_sources(None, None, None, None))
            checks = gr.HTML(render_checks(None))

        refresh_inputs = [title, options, lead, cta, tags, cover, cover_cap, *paras, *picks, *caps, editor_state]
        refresh_outputs = [effect, checks, export_box]
        for box in (title, options, lead, cta, tags, cover_cap, *paras, *caps):
            box.change(refresh, refresh_inputs, refresh_outputs, trigger_mode="always_last")

        def _bind_pick(picker, caption):
            picker.input(lambda name, current: caption_for(name, current or {}), [picker, editor_state], caption).then(
                refresh, refresh_inputs, refresh_outputs
            )

        _bind_pick(cover, cover_cap)
        for picker, caption in zip(picks, caps):
            _bind_pick(picker, caption)
        gallery.select(on_pick, [focus, editor_state], [cover, *picks, cover_cap, *caps]).then(
            refresh, refresh_inputs, refresh_outputs
        )

        outputs = [
            effect,
            sources,
            checks,
            editor_state,
            status,
            export_box,
            title,
            options,
            lead,
            cta,
            tags,
            cover,
            cover_cap,
            focus,
            gallery,
            *groups,
            *paras,
            *picks,
            *caps,
            product,
            audience,
            scene,
            platform,
            note,
        ]
        test_button.click(test_connection, outputs=[connection, status])
        button.click(generate, [product, audience, scene, platform, note, brief], outputs)
    return demo


if __name__ == "__main__":
    build_demo().launch(
        server_name="127.0.0.1",
        server_port=7860,
        css=PAGE_CSS,
        allowed_paths=[str(KB_ROOT), str(ROOT / "cache")],
    )
