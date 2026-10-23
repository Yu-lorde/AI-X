---
title: 懂你所需营销内容工作台
license: apache-2.0
sdk: docker
app_port: 7860
---

# 懂你所需 · 营销内容工作台

华为终端营销软文智能体。输入一条需求（或一句话描述），程序先检索产品知识库，再按平台模板成稿，并逐项核验产品事实与合规用语。

## 功能

- 一句话需求解析：自动填入产品型号、目标读者、业务场景、发布平台和写作视角。
- 知识库检索：产品事实只来自 P1 型号资料，场景骨架来自 P8，篇幅与结构来自 P6 平台模板。
- 生成与核验：成稿附参考资料与待确认信息，产品参数、配图型号、绝对化用语逐项检查。
- 合规检查：小红书等平台拦截第一人称虚构购买/使用经历、身份代入开头、无依据使用时长。
- 编辑与版本：左侧编辑文字与配图，右侧实时预览；每次保存生成一个版本，可回溯。
- 历史作品：按访客 Cookie 隔离，仅显示本周期的生成记录。
- 门店海报：在导出页把当前文稿排成本地 A4 竖版 PNG，不调用外部图片模型。

## 目录结构

```
agent/     生成与核验：检索、提示词、合规、成稿流水线
server/    FastAPI 后端：接口、历史存储、海报排版
web/       React + Vite 前端：首页、工作台、历史页
知识库/    P1 产品事实、P6 平台模板、P8 场景与画像
docs/      提示词结构、技术架构、开发记录
```

## 检索顺序

与知识库 README 的调用顺序一致：

1. 识别平台、受众、场景和型号。人群对不上唯一行业模块时先追问。
2. 用受众映射 P8 母文档，例如开学季的教育管理者进入《教育场景问题》，再进入 `06-教育管理`。
3. 从 ima 读取母文档，以及该模块的客户画像、问题清单、方案输出模板、验收清单、完整参考案例。
4. 产品参数只检索标题中带有产品事实、规格或参数的 P1 资料。价格不从软文推断。
5. 按所选平台从 ima 读取 `P6-营销素材库/02-平台模板` 中对应的创作指南，成稿的篇幅、结构和图片节奏以该模板为准。
6. 按 P8 方案输出模板组织任务，再按平台模板改写成稿。问题清单里没有回答的项目保持待确认。
7. 图片只使用本次检索到、且型号一致的文件。

## 环境

- Python 3.11 或更高版本
- Node.js 18 或更高版本
- 已解压的官方脚本 `ima-skill/ima_api.cjs`
- ima 的 Client ID、API Key
- 一个兼容 OpenAI 接口的大模型密钥

## 配置

复制 `agent/.env.example` 为 `agent/.env` 后填写；也可以在当前 PowerShell 里直接设置环境变量，环境变量优先。密钥不要写进代码，也不要提交到 GitHub。

```powershell
$env:IMA_OPENAPI_CLIENTID="你的ClientID"
$env:IMA_OPENAPI_APIKEY="你的APIKey"
$env:LLM_API_KEY="你的大模型密钥"
$env:LLM_BASE_URL="https://api.deepseek.com/v1"
$env:LLM_MODEL="deepseek-chat"
```

通义千问可以把地址改为 `https://dashscope.aliyuncs.com/compatible-mode/v1`，模型填 `qwen-plus`。

官方脚本如果不在默认位置，再设置：

```powershell
$env:IMA_SKILL_SCRIPT="C:\Users\ROG\Downloads\ima-skills-1.1.10\ima-skill\ima_api.cjs"
```

## 运行

后端：

```powershell
.venv\Scripts\python.exe -m server.main
```

浏览器打开 http://127.0.0.1:8000 。构建过 `web/dist` 时由后端直接托管前端，未构建时页面会提示先执行构建。

前端开发（热更新，接口转发到 8000）：

```powershell
cd web
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:5173 。

构建前端：

```powershell
cd web
npm run build
```

产物输出到 `web/dist`，刷新 http://127.0.0.1:8000 即可看到最新页面。

## 本地检查

```powershell
.venv\Scripts\python.exe agent\test_core.py
cd web; npx tsc --noEmit
```

## 数据与隐私

- 历史记录存于 `server/data/history.db`（SQLite），不保存密钥、环境变量或完整调试日志。
- 访客标识使用 HttpOnly Cookie，不写入 URL，不提供注册登录。
- `.env`、`server/data/`、本地知识库压缩包与赛题资料均已忽略，不进入版本库。

## 已知限制

- 正文生成依赖 `LLM_API_KEY`。没有密钥时，程序仍会检索并说明停在哪一步。
- 图片只使用本次 ima 检索返回、且标题对应该型号的文件。检索不到图片时不配图。
- PDF 原文如果接口只给二进制，程序使用检索摘要，并在核验里保留资料标题。
- 知识库没有的价格、补贴、库存不会被写成确定信息。
