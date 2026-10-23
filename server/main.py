"""FastAPI 入口。开发时前端跑 Vite，构建后由这里直接托管 web/dist。"""

from __future__ import annotations

from . import bootstrap

bootstrap.boot()

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from . import api, history_service  # noqa: E402
from .config import COOKIE_MAX_AGE, COOKIE_NAME, WEB_DIST  # noqa: E402

app = FastAPI(title="AI+X 营销软文工作台", docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.middleware("http")
async def visitor_cookie(request: Request, call_next):
    token = request.cookies.get(COOKIE_NAME)
    needs_new = not history_service.valid_visitor_id(token)
    visitor = history_service.new_visitor_id() if needs_new else token
    request.state.visitor = visitor
    response = await call_next(request)
    if needs_new:
        response.set_cookie(
            COOKIE_NAME,
            visitor,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return response


app.include_router(api.router, prefix="/api")

if (WEB_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIST / "assets")), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    if full_path.startswith("api/"):
        return HTMLResponse("接口不存在", status_code=404)
    target = WEB_DIST / full_path
    if full_path and target.is_file():
        return FileResponse(target)
    index = WEB_DIST / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-store"})
    return HTMLResponse(
        "<div style='font-family:system-ui;padding:48px;line-height:1.8'>"
        "<h2>前端还没有构建</h2>"
        "<p>请在 <code>web/</code> 目录执行 <code>npm install</code> 和 <code>npm run build</code>，"
        "或运行 <code>npm run dev</code> 使用开发服务器。</p></div>",
        status_code=503,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.main:app", host="127.0.0.1", port=8000, reload=False)
