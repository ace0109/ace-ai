from functools import lru_cache
from typing import List, Dict, Optional
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.config import settings

# --- 配置 ---
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
VECTOR_STORE_PATH = settings.VECTOR_STORE_PATH


class RAGService:
    def __init__(self):
        # 初始化 Embedding 模型
        self.embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )

        # 初始化向量数据库 (Chroma)
        # persist_directory 指定数据保存的本地路径
        self.vector_store = Chroma(
            persist_directory=VECTOR_STORE_PATH, embedding_function=self.embeddings
        )

    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
    ):
        """
        将文本列表存入向量数据库

        Args:
            texts: 文本内容列表
            metadatas: 元数据列表（可选），每个文本对应一个字典
            ids: 文档 ID 列表（可选），用于追踪和删除
        """
        documents = [
            Document(page_content=text, metadata=metadatas[i] if metadatas else {})
            for i, text in enumerate(texts)
        ]
        self.vector_store.add_documents(documents, ids=ids)
        # Chroma 现在的版本通常会自动持久化

    def reset(self):
        """
        清空向量数据库
        """
        # 删除集合
        self.vector_store.delete_collection()
        # 重新初始化
        self.vector_store = Chroma(
            persist_directory=VECTOR_STORE_PATH, embedding_function=self.embeddings
        )

    def query(self, query_text: str, k: int = 3) -> List[Document]:
        """
        根据问题检索最相关的 k 个文档片段
        """
        # similarity_search 会返回最相似的文档
        return self.vector_store.similarity_search(query_text, k=k)

    def get_all_documents(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> Dict:
        """
        获取所有文档
        返回格式: {"ids": [...], "documents": [...], "metadatas": [...]}
        """
        try:
            # 显式指定 include，避免获取 embeddings (数据量大)
            return self.vector_store.get(
                include=["metadatas", "documents"], limit=limit, offset=offset
            )
        except Exception as e:
            print(f"获取文档列表失败: {e}")
            return {"ids": [], "documents": [], "metadatas": []}

    def delete_document(self, doc_id: str) -> bool:
        """
        根据 ID 删除文档
        """
        try:
            self.vector_store.delete(ids=[doc_id])
            return True
        except Exception as e:
            print(f"删除文档失败: {e}")
            return False

    def delete_documents_by_filter(self, filter_dict: Dict) -> bool:
        """
        根据 metadata 过滤条件批量删除文档
        """
        try:
            self.vector_store.delete(where=filter_dict)
            return True
        except Exception as e:
            print(f"批量删除失败: {e}")
            return False

    def get_documents_by_filter(self, filter_dict: Dict) -> Dict:
        """
        根据 metadata 获取文档（用于统计等）
        """
        try:
            return self.vector_store.get(where=filter_dict, include=["metadatas"])
        except Exception as e:
            return {"ids": [], "documents": [], "metadatas": []}

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """
        获取单个文档的详细信息
        """
        try:
            result = self.vector_store.get(ids=[doc_id])
            if result["ids"]:
                return {
                    "id": result["ids"][0],
                    "content": result["documents"][0],
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                }
            return None
        except Exception as e:
            print(f"获取文档失败: {e}")
            return None


@lru_cache
def get_rag_service() -> RAGService:
    """
    延迟创建 RAGService，避免应用启动时阻塞（例如等待 Ollama 模型加载）。
    """
    return RAGService()
