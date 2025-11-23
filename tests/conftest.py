import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.api.routes import get_llm
from app.main import app
from app.services.key_store import key_store


class FakeDocument:
    def __init__(self, content: str, metadata: dict | None = None):
        self.page_content = content
        self.metadata = metadata or {}


class FakeStreamChunk:
    def __init__(self, content: str):
        self._content = content

    def model_dump(self) -> dict:
        return {"content": self._content}


class FakeLLM:
    async def astream(self, messages):
        yield FakeStreamChunk("stream chunk")


class FakeRAGService:
    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}
        self.counter = 0

    def add_documents(self, texts, metadatas=None, ids=None):
        for idx, text in enumerate(texts):
            doc_id = ids[idx] if ids else f"doc-{self.counter}"
            self.counter += 1
            metadata = metadatas[idx] if metadatas else {}
            self.docs[doc_id] = {"content": text, "metadata": metadata}

    def reset(self):
        self.docs.clear()

    def query(self, query_text: str, k: int = 3):
        items = list(self.docs.items())[:k]
        return [FakeDocument(payload["content"], payload["metadata"]) for _, payload in items]

    def get_all_documents(self, limit=None, offset=None):
        ids = list(self.docs.keys())
        start = offset or 0
        end = start + limit if limit is not None else None
        sliced_ids = ids[start:end]
        documents = [self.docs[i]["content"] for i in sliced_ids]
        metadatas = [self.docs[i]["metadata"] for i in sliced_ids]
        return {"ids": sliced_ids, "documents": documents, "metadatas": metadatas}

    def get_document(self, doc_id: str):
        if doc_id in self.docs:
            payload = self.docs[doc_id]
            return {"id": doc_id, "content": payload["content"], "metadata": payload["metadata"]}
        return None

    def delete_document(self, doc_id: str) -> bool:
        return self.docs.pop(doc_id, None) is not None

    def delete_documents_by_filter(self, filter_dict: dict) -> bool:
        matches = [doc_id for doc_id, payload in self.docs.items() if self._match_filter(payload["metadata"], filter_dict)]
        for doc_id in matches:
            self.docs.pop(doc_id, None)
        return True

    def get_documents_by_filter(self, filter_dict: dict):
        matches = [doc_id for doc_id, payload in self.docs.items() if self._match_filter(payload["metadata"], filter_dict)]
        return {
            "ids": matches,
            "documents": [self.docs[mid]["content"] for mid in matches],
            "metadatas": [self.docs[mid]["metadata"] for mid in matches],
        }

    @staticmethod
    def _match_filter(metadata: dict, filter_dict: dict) -> bool:
        for key, value in filter_dict.items():
            if metadata.get(key) != value:
                return False
        return True


@pytest.fixture
def fake_rag_service():
    return FakeRAGService()


@pytest.fixture
def client(fake_rag_service, monkeypatch):
    monkeypatch.setattr(routes, "get_rag_service", lambda: fake_rag_service)
    app.dependency_overrides[get_llm] = lambda: FakeLLM()

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def admin_api_key():
    created = key_store.create_key("admin", label="pytest-admin")
    return created["api_key"]


@pytest.fixture
def user_api_key():
    created = key_store.create_key("user", label="pytest-user")
    return created["api_key"]


@pytest.fixture
def admin_headers(admin_api_key):
    return {"X-API-Key": admin_api_key}


@pytest.fixture
def user_headers(user_api_key):
    return {"X-API-Key": user_api_key}
