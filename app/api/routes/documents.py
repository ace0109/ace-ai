"""文档和知识库管理接口"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.api.deps import text_splitter
from app.core.auth import require_super_admin_key
from app.services.rag import get_rag_service
from app.utils.file_parsers import parse_file_content
from app.schemas import (
    UnifiedResponse,
    IngestRequest,
    DocumentResponse,
    DocumentListResponse,
)


router = APIRouter(tags=["Documents"])
# 注意：API Key 认证已在 api/__init__.py 的路由注册时配置


@router.post("/ingest", summary="Add text to knowledge base", response_model=UnifiedResponse[Dict[str, str]])
async def ingest_text(request: IngestRequest):
    """
    接收文本并存入向量数据库
    """
    if not request.text.strip():
        return UnifiedResponse(code="400", message="Text cannot be empty", data={"status": "error"})

    rag_service = get_rag_service()
    metadata = {
        "source": request.source or "manual_input",
        "upload_time": datetime.now(timezone.utc).isoformat(),
    }
    await run_in_threadpool(rag_service.add_documents, [request.text], metadatas=[metadata])
    return UnifiedResponse(data={"status": "success", "message": "Data ingested successfully"})


@router.post("/reset", summary="Reset knowledge base", response_model=UnifiedResponse[Dict[str, str]])
async def reset_knowledge_base(_: dict = Depends(require_super_admin_key)):
    """
    清空知识库（仅超级管理员可操作）
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
    allowed_extensions = [".txt", ".pdf", ".md", ".markdown"]
    filename = file.filename or ""
    file_ext = "." + filename.split(".")[-1].lower() if "." in filename else ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。请上传 {', '.join(allowed_extensions)} 文件",
        )

    # 2. 读取文件内容
    # 增加大小限制 (例如 10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # 检查 Content-Length 头（如果存在）
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件过大，最大允许 10MB")

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件过大，最大允许 10MB")

    # 3. 根据文件类型解析
    try:
        text = parse_file_content(content, file_ext)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 4. 文本分割
    chunks = text_splitter.split_text(text)

    # 检查是否有有效的 chunk
    if not chunks:
        raise HTTPException(status_code=400, detail="文件内容过短，无法生成有效的文档块")

    # 5. 生成唯一的文档 ID
    # 使用 UUID 避免文件名中的特殊字符导致 ID 问题，同时保留文件名在 metadata 中
    base_id = str(uuid.uuid4())
    filename = file.filename or "untitled"

    # 为每个 chunk 生成 ID 和 metadata
    chunk_ids = [f"{base_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source": filename,
            "upload_time": datetime.now(timezone.utc).isoformat(),
            "file_type": file_ext,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "batch_id": base_id,
        }
        for i in range(len(chunks))
    ]

    # 6. 存入向量数据库
    try:
        rag_service = get_rag_service()
        await run_in_threadpool(rag_service.add_documents, chunks, metadatas=metadatas, ids=chunk_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"存储失败: {str(e)}")

    return UnifiedResponse(
        data={
            "status": "success",
            "message": f"文件 '{filename}' 上传成功",
            "filename": filename,
            "chunks_created": len(chunks),
            "base_id": base_id,
        }
    )


@router.get("/documents", response_model=UnifiedResponse[DocumentListResponse], summary="列出所有文档")
async def list_documents(limit: int = 100, offset: int = 0):
    """
    获取知识库中的所有文档 (支持分页)

    注意：每个文件可能被切分成多个 chunk，这里会返回所有 chunk
    """
    rag_service = get_rag_service()
    
    # 获取文档总数（用于分页）
    total = await run_in_threadpool(rag_service.count_documents)
    
    # 获取当前页的文档
    data = await run_in_threadpool(rag_service.get_all_documents, limit=limit, offset=offset)

    documents = []
    if data["ids"]:
        for i in range(len(data["ids"])):
            content = data["documents"][i]
            # 截断显示内容
            display_content = content[:200] + "..." if len(content) > 200 else content

            documents.append(
                DocumentResponse(
                    id=data["ids"][i],
                    content=display_content,
                    metadata=data["metadatas"][i] if (data["metadatas"] and data["metadatas"][i] is not None) else {},
                )
            )

    return UnifiedResponse(data=DocumentListResponse(total=total, documents=documents))


@router.get("/documents/{doc_id}", response_model=UnifiedResponse[DocumentResponse], summary="获取单个文档详情")
async def get_document(doc_id: str):
    """
    根据 ID 获取文档的完整内容
    """
    rag_service = get_rag_service()
    doc = await run_in_threadpool(rag_service.get_document, doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    return UnifiedResponse(data=DocumentResponse(id=doc["id"], content=doc["content"], metadata=doc["metadata"]))


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
async def delete_documents_by_source(source: str, _: dict = Depends(require_super_admin_key)):
    """
    删除指定文件名的所有 chunk（仅超级管理员可操作）

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
    success = await run_in_threadpool(rag_service.delete_documents_by_filter, filter_dict)

    if not success:
        raise HTTPException(status_code=500, detail="删除失败")

    return UnifiedResponse(
        data={"status": "success", "message": f"已删除 {count} 个文档块", "source": source, "deleted_count": count}
    )
