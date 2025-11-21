"""API Key 认证依赖：从数据库校验，而非环境变量。"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.services.key_store import key_store, Role

API_KEY_HEADER_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


async def require_api_key(api_key: str = Security(api_key_header)) -> dict:
    """
    校验传入的 API Key，返回 key 记录（不含明文）。
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
