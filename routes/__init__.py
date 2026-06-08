"""路由注册 — 创建 FastAPI 应用并注册所有路由"""
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routes.story import router as story_router
from routes.drafts import router as drafts_router
from routes.beats import router as beats_router
from routes.chapters import router as chapters_router
from routes.outline import router as outline_router
from routes.characters import router as characters_router
from routes.writing import router as writing_router
from routes.ai_panel import router as ai_panel_router


def create_app():
    app = FastAPI(title="故事创作助手 v3")

    # 注册 API 路由
    app.include_router(story_router)
    app.include_router(drafts_router)
    app.include_router(beats_router)
    app.include_router(chapters_router)
    app.include_router(outline_router)
    app.include_router(characters_router)
    app.include_router(writing_router)
    app.include_router(ai_panel_router)

    # 静态文件（前端）
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
    os.makedirs(frontend_dir, exist_ok=True)
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app
