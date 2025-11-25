import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

class Settings:
    # App
    APP_TITLE: str = "Ace AI"
    APP_VERSION: str = "0.1.0"
    
    # Model
    # 默认使用 qwen3-coder:480b-cloud，也可通过环境变量覆盖
    MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen3-coder:480b-cloud")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    OLLAMA_BASE_URL: Optional[str] = os.getenv("OLLAMA_BASE_URL", None)
    
    # RAG
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "./chroma_db")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    # Prompt
    SYSTEM_PROMPT: str = os.getenv("SYSTEM_PROMPT", "用中文回复。结尾注明：-- 来自Ace AI")

    # Security
    API_KEY_HEADER_NAME: str = "X-API-Key"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
