"""API Key 管理接口"""

from typing import Dict
from fastapi import APIRouter, Depends

from app.core.auth import require_admin_key
from app.services.key_store import key_store
from app.schemas import (
    UnifiedResponse,
    APIKeyCreateRequest,
    APIKeyCreateResponse,
)


router = APIRouter(prefix="/keys", tags=["Authentication"])


@router.post("", response_model=UnifiedResponse[APIKeyCreateResponse], summary="生成 API Key")
async def create_api_key(
    payload: APIKeyCreateRequest, _: dict = Depends(require_admin_key)
):
    """
    仅管理员可调用，生成新的 API Key；明文只在创建时返回一次。
    """
    created = key_store.create_key(role=payload.role, label=payload.label)
    return UnifiedResponse(data=APIKeyCreateResponse(**created))


@router.get(
    "",
    summary="列出已存在的 API Key（隐藏明文）",
    response_model=UnifiedResponse[Dict[str, list]],
)
async def list_api_keys(_: dict = Depends(require_admin_key)):
    """
    仅管理员可调用，用于查看已有 key 的角色、标签及创建时间。
    """
    return UnifiedResponse(data=key_store.list_keys())
