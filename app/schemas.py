from typing import Generic, TypeVar, Optional, List, get_args
from pydantic import BaseModel, field_validator
from app.services.key_store import Role

T = TypeVar("T")

class UnifiedResponse(BaseModel, Generic[T]):
    code: str = "200"
    message: str = "success"
    data: Optional[T] = None

# --- Existing Models moved/refactored here or just kept for type safety ---

class MessageBody(BaseModel):
    message: str
    session_id: Optional[str] = None

class SessionResponse(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str

class IngestRequest(BaseModel):
    text: str

class DocumentResponse(BaseModel):
    id: str
    content: str
    metadata: dict

class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentResponse]

class APIKeyCreateRequest(BaseModel):
    role: Role
    label: str | None = None

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> Role:
        """验证并转换 role 为正确的 Literal 类型"""
        allowed_roles = get_args(Role)
        if v not in allowed_roles:
            raise ValueError(f"role must be one of {allowed_roles}")
        return v  # type: ignore

class APIKeyCreateResponse(BaseModel):
    api_key: str
    role: Role
    label: str | None
    created_at: str
