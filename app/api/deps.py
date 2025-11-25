"""共享的依赖项和工具函数"""

from functools import lru_cache
from langchain_ollama import ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


@lru_cache
def get_llm() -> ChatOllama:
    """获取 LLM 实例（单例模式）"""
    return ChatOllama(
        model=settings.MODEL_NAME,
        temperature=0,
        base_url=settings.OLLAMA_BASE_URL,
    )


# 配置文本分割器
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
)
