"""API Key 认证依赖：从数据库校验，而非环境变量。"""

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from app.services.key_store import key_store, Role

API_KEY_HEADER_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


async def require_api_key(request: Request, api_key: str = Security(api_key_header)) -> dict:
    """
    校验传入的 API Key，返回 key 记录（不含明文）。
    结果会存储到 request.state.api_key_record 供后续使用。
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "API key"},
        )

    record = key_store.verify_key(api_key)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "API key"},
        )
    # 存储到 request.state 供端点函数使用
    request.state.api_key_record = record
    return record


async def get_current_api_key(request: Request) -> dict:
    """
    从 request.state 获取已验证的 API Key 记录。
    用于路由级依赖已完成认证后，端点获取认证信息。
    """
    record = getattr(request.state, "api_key_record", None)
    if not record:
        # 如果路由级没有认证，则执行认证
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key not authenticated",
        )
    return record


async def require_admin_key(key_record: dict = Depends(require_api_key)) -> dict:
    """
    仅允许 admin 或 super_admin 使用的依赖。
    """
    role: Role = key_record.get("role")  # type: ignore
    if role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return key_record


async def require_super_admin_key(request: Request) -> dict:
    """
    仅允许 super_admin 使用的依赖。
    用于危险操作如重置知识库、批量删除等。
    """
    record = getattr(request.state, "api_key_record", None)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key not authenticated",
        )
    role: Role = record.get("role")  # type: ignore
    if role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required",
        )
    return record
