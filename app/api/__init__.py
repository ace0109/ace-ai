"""API router package."""

from fastapi import APIRouter, Depends

from app.api.routes import health, auth, chat, documents
from app.core.auth import require_api_key, require_admin_key

# 创建主路由器（不添加全局认证，各路由自行控制）
router = APIRouter(prefix="/api")

# Health 接口不需要认证
router.include_router(health.router)

# Auth 接口需要管理员权限
router.include_router(auth.router, dependencies=[Depends(require_admin_key)])

# Chat 接口需要 API Key
router.include_router(chat.router, dependencies=[Depends(require_api_key)])

# Documents 接口需要 API Key
router.include_router(documents.router, dependencies=[Depends(require_api_key)])

__all__ = ["router"]
