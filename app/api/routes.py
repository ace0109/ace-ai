"""API 模块：提供受保护的知识库管理与维护接口。"""

import json
import uuid
from datetime import datetime
from functools import lru_cache
from typing import Any, AsyncIterator, List, Optional, Dict

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from langchain_ollama import ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel

from app.core.auth import require_admin_key, require_api_key
from app.core.config import settings
from app.services.key_store import key_store, Role
from app.services.rag import get_rag_service
from app.services.chat_store import chat_store
from app.utils.file_parsers import parse_file_content
from app.schemas import (
    UnifiedResponse,
    MessageBody,
    SessionResponse,
    MessageResponse,
    IngestRequest,
    DocumentResponse,
    DocumentListResponse,
    APIKeyCreateRequest,
    APIKeyCreateResponse
)

router = APIRouter(
    prefix="/api",
    tags=["API"],
)

# --- 配置区域 ---
# Config handled by settings

@lru_cache
def get_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.MODEL_NAME,
        temperature=0,
        # keep_alive="5m", # 可选：保持模型加载状态
    )

# 配置文本分割器
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
)


# --- 辅助函数：文件解析 ---
# Moved to app.utils.file_parsers


# --- API 接口 ---

@router.get("/health", summary="Health check", response_model=UnifiedResponse[Dict[str, str]])
async def health():
    """
    健康检查接口
    """
    return UnifiedResponse(data={"status": "ok"})


@router.post("/keys", response_model=UnifiedResponse[APIKeyCreateResponse], summary="生成 API Key")
async def create_api_key(payload: APIKeyCreateRequest, _: dict = Depends(require_admin_key)):
    """
    仅管理员可调用，生成新的 API Key；明文只在创建时返回一次。
    """
    created = key_store.create_key(role=payload.role, label=payload.label)
    return UnifiedResponse(data=APIKeyCreateResponse(**created))


@router.get("/keys", summary="列出已存在的 API Key（隐藏明文）", response_model=UnifiedResponse[Dict[str, list]])
async def list_api_keys(_: dict = Depends(require_admin_key)):
    """
    仅管理员可调用，用于查看已有 key 的角色、标签及创建时间。
    """
    return UnifiedResponse(data=key_store.list_keys())


# --- Chat Session Endpoints ---

@router.get("/chat/sessions", response_model=UnifiedResponse[List[SessionResponse]], summary="获取会话列表")
async def list_chat_sessions(api_key_record: dict = Depends(require_api_key)):
    sessions = await run_in_threadpool(chat_store.list_sessions, api_key_record["id"])
    return UnifiedResponse(data=sessions)


@router.delete("/chat/sessions/{session_id}", summary="删除会话", response_model=UnifiedResponse[Dict[str, str]])
async def delete_chat_session(session_id: str, api_key_record: dict = Depends(require_api_key)):
    success = await run_in_threadpool(chat_store.delete_session, session_id, api_key_record["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return UnifiedResponse(data={"status": "success"})


@router.get("/chat/sessions/{session_id}/messages", response_model=UnifiedResponse[List[MessageResponse]], summary="获取会话消息记录")
async def get_chat_messages(session_id: str, api_key_record: dict = Depends(require_api_key)):
    # Verify ownership
    session = await run_in_threadpool(chat_store.get_session, session_id, api_key_record["id"])
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await run_in_threadpool(chat_store.get_messages, session_id)
    return UnifiedResponse(data=messages)


@router.post("/chat", summary="Chat with Ollama")
async def chat_with_ollama(
    messageBody: MessageBody,
    llm: ChatOllama = Depends(get_llm),
    api_key_record: dict = Depends(require_api_key),
):
    """
    进行聊天并使用 RAG 结果增强回答。
    """
    # 1. Handle Session
    session_id = messageBody.session_id
    if not session_id:
        # Create new session
        session = await run_in_threadpool(chat_store.create_session, api_key_record["id"], name=messageBody.message[:20])
        session_id = session["id"]
    else:
        # Verify session exists and belongs to user
        session = await run_in_threadpool(chat_store.get_session, session_id, api_key_record["id"])
        if not session:
             raise HTTPException(status_code=404, detail="Session not found")

    # 2. Save User Message
    await run_in_threadpool(chat_store.add_message, session_id, "user", messageBody.message)

    # 3. Get History & RAG
    history = await run_in_threadpool(chat_store.get_messages, session_id)
    # Filter last N messages to avoid context overflow? For now, take last 10.
    recent_history = history[-10:] 
    
    rag_service = get_rag_service()
    relevant_docs = await run_in_threadpool(rag_service.query, messageBody.message, k=3)
    context_text = "\n\n".join([doc.page_content for doc in relevant_docs])

    system_prompt = settings.SYSTEM_PROMPT
    if context_text:
        system_prompt += (
            f"\n\n请基于以下【已知信息】回答用户的问题。如果无法从已知信息中得到答案，请如实说明。\n\n"
            f"【已知信息】:\n{context_text}"
        )
    
    messages = [("system", system_prompt)]
    for msg in recent_history:
        role = "human" if msg['role'] == "user" else "ai"
        messages.append((role, msg['content']))

    async def stream_response() -> AsyncIterator[str]:
        full_response = ""
        # Yield session_id first so client knows it
        yield f"data: {json.dumps({'session_id': session_id}, ensure_ascii=False)}\n\n"
        
        try:
            async for chunk in llm.astream(messages):
                content = ""
                if hasattr(chunk, "model_dump"):
                    payload: Any = chunk.model_dump()
                    content = payload.get("content", "")
                else:
                    content = str(chunk)
                    payload = {"content": content}

                full_response += content
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            
            # Save Assistant Message after streaming is done
            await run_in_threadpool(chat_store.add_message, session_id, "assistant", full_response)
            
        except Exception as e:
            error_payload = {"error": str(e), "content": f"\n[System Error]: {str(e)}"}
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


@router.post("/ingest", summary="Add text to knowledge base", response_model=UnifiedResponse[Dict[str, str]])
async def ingest_text(request: IngestRequest):
    """
    接收文本并存入向量数据库
    """
    if not request.text.strip():
        return UnifiedResponse(code="400", message="Text cannot be empty", data={"status": "error"})

    rag_service = get_rag_service()
    await run_in_threadpool(rag_service.add_documents, [request.text])
    return UnifiedResponse(data={"status": "success", "message": "Data ingested successfully"})


@router.post("/reset", summary="Reset knowledge base", response_model=UnifiedResponse[Dict[str, str]])
async def reset_knowledge_base():
    """
    清空知识库
    """
    rag_service = get_rag_service()
    await run_in_threadpool(rag_service.reset)
    return UnifiedResponse(data={"status": "success", "message": "Knowledge base reset successfully"})


@router.post("/documents/upload", summary="上传文档到知识库", response_model=UnifiedResponse[Dict[str, Any]])
async def upload_document(file: UploadFile = File(...)):
    """
    上传文件（支持 .txt, .pdf, .md）
    
    - 文件会被自动切分成多个块（chunk）
    - 每个块共享同一个 source（文件名）
    - 返回上传成功的文档数量
    """
    # 1. 检查文件类型
    allowed_extensions = ['.txt', '.pdf', '.md', '.markdown']
    filename = file.filename or ""
    file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件类型。请上传 {', '.join(allowed_extensions)} 文件"
        )
    
    # 2. 读取文件内容
    content = await file.read()
    
    # 3. 根据文件类型解析
    try:
        text = parse_file_content(content, file_ext)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")
    
    if not text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")
    
    # 4. 文本分割
    chunks = text_splitter.split_text(text)
    
    # 5. 生成唯一的文档 ID
    # 使用 UUID 避免文件名中的特殊字符导致 ID 问题，同时保留文件名在 metadata 中
    base_id = str(uuid.uuid4())
    filename = file.filename or "untitled"
    
    # 为每个 chunk 生成 ID 和 metadata
    chunk_ids = [f"{base_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source": filename,
            "upload_time": datetime.now().isoformat(),
            "file_type": file_ext,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "batch_id": base_id
        }
        for i in range(len(chunks))
    ]
    
    # 6. 存入向量数据库
    try:
        rag_service = get_rag_service()
        await run_in_threadpool(rag_service.add_documents, chunks, metadatas=metadatas, ids=chunk_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"存储失败: {str(e)}")
    
    return UnifiedResponse(data={
        "status": "success",
        "message": f"文件 '{filename}' 上传成功",
        "filename": filename,
        "chunks_created": len(chunks),
        "base_id": base_id
    })


@router.get("/documents", response_model=UnifiedResponse[DocumentListResponse], summary="列出所有文档")
async def list_documents(limit: int = 100, offset: int = 0):
    """
    获取知识库中的所有文档 (支持分页)
    
    注意：每个文件可能被切分成多个 chunk，这里会返回所有 chunk
    """
    rag_service = get_rag_service()
    data = await run_in_threadpool(rag_service.get_all_documents, limit=limit, offset=offset)
    
    documents = []
    if data["ids"]:
        for i in range(len(data["ids"])):
            content = data["documents"][i]
            # 截断显示内容
            display_content = content[:200] + "..." if len(content) > 200 else content
            
            documents.append(DocumentResponse(
                id=data["ids"][i],
                content=display_content,
                metadata=data["metadatas"][i] if (data["metadatas"] and data["metadatas"][i] is not None) else {}
            ))
    
    return UnifiedResponse(data=DocumentListResponse(total=len(documents), documents=documents))


@router.get("/documents/{doc_id}", response_model=UnifiedResponse[DocumentResponse], summary="获取单个文档详情")
async def get_document(doc_id: str):
    """
    根据 ID 获取文档的完整内容
    """
    rag_service = get_rag_service()
    doc = await run_in_threadpool(rag_service.get_document, doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    return UnifiedResponse(data=DocumentResponse(
        id=doc["id"],
        content=doc["content"],
        metadata=doc["metadata"]
    ))


@router.delete("/documents/{doc_id}", summary="删除文档", response_model=UnifiedResponse[Dict[str, str]])
async def delete_document(doc_id: str):
    """
    根据 ID 删除文档
    
    注意：如果文件被切分成多个 chunk，需要分别删除每个 chunk
    """
    rag_service = get_rag_service()
    success = await run_in_threadpool(rag_service.delete_document, doc_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在或删除失败")
    
    return UnifiedResponse(data={"status": "success", "message": f"文档 {doc_id} 已删除"})


@router.delete("/documents/batch/by-source", summary="批量删除文档（按文件名）", response_model=UnifiedResponse[Dict[str, Any]])
async def delete_documents_by_source(source: str):
    """
    删除指定文件名的所有 chunk
    
    参数:
        source: 文件名（例如 "manual.pdf"）
    """
    # 1. 先查询匹配的文档数量（用于返回给前端）
    filter_dict = {"source": source}
    rag_service = get_rag_service()
    docs = await run_in_threadpool(rag_service.get_documents_by_filter, filter_dict)
    count = len(docs["ids"]) if docs and "ids" in docs else 0
    
    if count == 0:
        raise HTTPException(status_code=404, detail=f"未找到来源为 '{source}' 的文档")
    
    # 2. 批量删除
    rag_service = get_rag_service()
    success = await run_in_threadpool(rag_service.delete_documents_by_filter, filter_dict)
    
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")
    
    return UnifiedResponse(data={
        "status": "success",
        "message": f"已删除 {count} 个文档块",
        "source": source,
        "deleted_count": count
    })
