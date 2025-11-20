import json
from functools import lru_cache
from typing import Any, AsyncIterator

from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from langchain_ollama import ChatOllama
from pydantic import BaseModel

from app.rag import rag_service
from app.admin import router as admin_router

# --- 配置区域 ---
MODEL_NAME = "qwen3-coder:30b"
# MODEL_NAME = "deepseek-r1:8b"
SYSTEM_PROMPT = "用中文回复。结尾注明：-- 来自Ace AI"

class MessageBody(BaseModel):
    message: str

class IngestRequest(BaseModel):
    text: str

# 使用 lru_cache 缓存 LLM 客户端实例，避免每次请求重复创建
@lru_cache
def get_llm() -> ChatOllama:
    return ChatOllama(
        model=MODEL_NAME,
        temperature=0,
        # keep_alive="5m", # 可选：保持模型加载状态
    )


def create_app() -> FastAPI:
    """
    Build and return a FastAPI application instance.
    """
    app = FastAPI(title="Ace AI", version="0.1.0")
    
    # 注册 Admin Router
    app.include_router(admin_router)
    
    @app.post("/ingest", summary="Add text to knowledge base")
    async def ingest_text(request: IngestRequest):
        """
        接收文本并存入向量数据库
        """
        if not request.text.strip():
            return {"status": "error", "message": "Text cannot be empty"}
            
        rag_service.add_documents([request.text])
        return {"status": "success", "message": "Data ingested successfully"}

    @app.post("/reset", summary="Reset knowledge base")
    async def reset_knowledge_base():
        """
        清空知识库
        """
        rag_service.reset()
        return {"status": "success", "message": "Knowledge base reset successfully"}

    @app.post("/chat", summary="Chat with Ollama")
    async def chat_with_ollama(
        messageBody: MessageBody, 
        llm: ChatOllama = Depends(get_llm)
    ):
        # 1. RAG 检索：先去知识库查相关信息
        # 检索与用户问题最相关的 3 个片段
        relevant_docs = rag_service.query(messageBody.message, k=3)
        
        # 将检索到的文档内容拼接成字符串
        context_text = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        # 2. 构建增强的 Prompt
        # 如果找到了相关信息，就把它塞给 AI
        if context_text:
            system_prompt_with_context = (
                f"{SYSTEM_PROMPT}\n"
                f"请基于以下【已知信息】回答用户的问题。如果无法从已知信息中得到答案，请如实说明。\n\n"
                f"【已知信息】:\n{context_text}"
            )
        else:
            # 如果没查到，就用普通 Prompt
            system_prompt_with_context = SYSTEM_PROMPT

        messages = [
            ("system", system_prompt_with_context),
            ("human", messageBody.message),
        ]

        async def stream_response() -> AsyncIterator[str]:
            try:
                # 使用 astream 进行异步流式传输
                async for chunk in llm.astream(messages):
                    # 统一使用 model_dump (Pydantic v2 / LangChain Core)
                    if hasattr(chunk, "model_dump"):
                        payload: Any = chunk.model_dump()
                    else:
                        payload = {"content": str(chunk)}

                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            except Exception as e:
                # 简单捕获异常并返回给前端，避免连接直接中断
                error_payload = {"error": str(e), "content": f"\n[System Error]: {str(e)}"}
                yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

        return StreamingResponse(stream_response(), media_type="text/event-stream")
    
    return app


app = create_app()
