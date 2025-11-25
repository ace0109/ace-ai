"""聊天会话和对话接口"""

import json
from typing import Any, AsyncIterator, List, Dict
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from langchain_ollama import ChatOllama

from app.api.deps import get_llm
from app.core.auth import require_api_key
from app.core.config import settings
from app.services.chat_store import chat_store
from app.services.rag import get_rag_service
from app.schemas import (
    UnifiedResponse,
    MessageBody,
    SessionResponse,
    MessageResponse,
)


router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/sessions", response_model=UnifiedResponse[List[SessionResponse]], summary="获取会话列表")
async def list_chat_sessions(api_key_record: dict = Depends(require_api_key)):
    """获取当前用户的所有聊天会话"""
    sessions = await run_in_threadpool(chat_store.list_sessions, api_key_record["id"])
    return UnifiedResponse(data=sessions)


@router.delete("/sessions/{session_id}", summary="删除会话", response_model=UnifiedResponse[Dict[str, str]])
async def delete_chat_session(session_id: str, api_key_record: dict = Depends(require_api_key)):
    """删除指定的聊天会话"""
    success = await run_in_threadpool(chat_store.delete_session, session_id, api_key_record["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return UnifiedResponse(data={"status": "success"})


@router.get("/sessions/{session_id}/messages", response_model=UnifiedResponse[List[MessageResponse]], summary="获取会话消息记录")
async def get_chat_messages(session_id: str, api_key_record: dict = Depends(require_api_key)):
    """获取指定会话的所有消息记录"""
    # Verify ownership
    session = await run_in_threadpool(chat_store.get_session, session_id, api_key_record["id"])
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await run_in_threadpool(chat_store.get_messages, session_id)
    return UnifiedResponse(data=messages)


@router.post("", summary="Chat with Ollama")
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
        session = await run_in_threadpool(
            chat_store.create_session,
            api_key_record["id"],
            name=messageBody.message[:20],
        )
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
        role = "human" if msg["role"] == "user" else "ai"
        messages.append((role, msg["content"]))

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
