"""健康检查接口"""

from typing import Dict
from fastapi import APIRouter

from app.schemas import UnifiedResponse


router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check", response_model=UnifiedResponse[Dict[str, str]])
async def health():
    """
    健康检查接口
    """
    return UnifiedResponse(data={"status": "ok"})
