import os
from typing import List
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# --- 配置 ---
EMBEDDING_MODEL = "nomic-embed-text"
VECTOR_STORE_PATH = "./chroma_db"

class RAGService:
    def __init__(self):
        # 初始化 Embedding 模型
        self.embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
        
        # 初始化向量数据库 (Chroma)
        # persist_directory 指定数据保存的本地路径
        self.vector_store = Chroma(
            persist_directory=VECTOR_STORE_PATH,
            embedding_function=self.embeddings
        )

    def add_documents(self, texts: List[str]):
        """
        将文本列表存入向量数据库
        """
        documents = [Document(page_content=text) for text in texts]
        self.vector_store.add_documents(documents)
        # Chroma 现在的版本通常会自动持久化

    def reset(self):
        """
        清空向量数据库
        """
        # 删除集合
        self.vector_store.delete_collection()
        # 重新初始化
        self.vector_store = Chroma(
            persist_directory=VECTOR_STORE_PATH,
            embedding_function=self.embeddings
        )

    def query(self, query_text: str, k: int = 3) -> List[Document]:
        """
        根据问题检索最相关的 k 个文档片段
        """
        # similarity_search 会返回最相似的文档
        return self.vector_store.similarity_search(query_text, k=k)

# 创建全局单例实例
rag_service = RAGService()
