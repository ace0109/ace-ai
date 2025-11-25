"""API router package."""

from fastapi import APIRouter

from app.api.routes import health, auth, chat, documents

# 创建主路由器
router = APIRouter(prefix="/api")

# 注册各个子路由
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(chat.router)
router.include_router(documents.router)

__all__ = ["router"]
