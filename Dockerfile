# 魔搭创空间（Docker SDK）用。两阶段：node 构建前端 → python 跑后端并托管 web/dist。

# 1) 构建 React 前端
FROM node:18-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# 2) 后端运行环境（FastAPI + uvicorn，一个服务同时提供 /api 和前端）
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY agent ./agent
COPY server ./server
COPY ["知识库", "知识库"]
COPY ["范文库", "范文库"]
COPY README.md ./
COPY --from=web /web/dist ./web/dist

EXPOSE 7860
CMD ["python", "-m", "server.main"]
