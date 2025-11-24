# Ace AI

Ace AI 是一个基于 **FastAPI** 和 **RAG (Retrieval-Augmented Generation)** 技术的轻量级 AI 服务。它利用本地运行的 **Ollama** 模型提供嵌入（Embedding）和对话能力，并使用 **ChromaDB** 进行向量存储，支持文档上传、知识库管理以及基于知识库的问答。

## ✨ 核心特性

- **📚 RAG 知识库**: 支持上传 `.txt`, `.pdf`, `.md` 文档，自动切分并存入向量数据库。
- **🤖 本地 LLM 支持**: 深度集成 Ollama，默认使用 `qwen3-coder:480b-cloud` (可配置) 进行对话，`nomic-embed-text` 进行向量化。
- **🔐 安全认证**: 内置 API Key 管理系统（超级管理员/普通用户），保障接口安全。
- **🚀 容器化部署**: 提供 Docker 和 Docker Compose 配置，一键启动。
- **💾 数据持久化**: 向量数据和 API Key 数据均可持久化保存。

## 🛠 前置要求

1.  **Docker & Docker Compose**: 用于运行应用服务。
2.  **Ollama**: 需要在宿主机或网络可达的地方运行 Ollama 服务。
    - 确保已拉取所需的模型：
      ```bash
      ollama pull qwen3-coder:480b-cloud  # 或你自定义的 Chat 模型
      ollama pull nomic-embed-text        # Embedding 模型
      ```

## 🚀 快速开始 (Docker Compose)

这是最推荐的启动方式。

1.  **启动服务**
    ```bash
    docker-compose up -d
    ```
    服务将在 `http://localhost:8000` 启动。

2.  **查看日志**
    ```bash
    docker-compose logs -f
    ```

3.  **首次访问**
    - 首次启动时，系统会自动生成一个 **超级管理员 API Key**。
    - 查看生成的 Key：
      ```bash
      cat data/initial_superadmin_key.txt
      ```
    - 使用此 Key 访问 API 文档：`http://localhost:8000/docs`

## ⚙️ 配置说明

你可以通过修改 `docker-compose.yml` 中的 `environment` 部分或创建 `.env` 文件来配置服务。

| 环境变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `MODEL_NAME` | `qwen3-coder:480b-cloud` | 用于对话的 Ollama 模型名称 |
| `EMBEDDING_MODEL` | `nomic-embed-text` | 用于生成向量的 Ollama 模型名称 |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama 服务地址 (Docker 内需指向宿主机) |
| `VECTOR_STORE_PATH` | `/app/chroma_db` | 向量数据库内部路径 |
| `SYSTEM_PROMPT` | (见源码) | 系统提示词 |

> **注意**: 如果你在 Linux 上运行 Docker，`host.docker.internal` 可能无法直接解析。你可能需要在 `docker-compose.yml` 中添加 `extra_hosts` 配置，或者直接使用宿主机的 IP 地址。

## 🔌 API 使用指南

所有接口均需在 Header 中携带 `X-API-Key`。

### 1. 健康检查
```http
GET /api/health
```

### 2. 上传文档 (构建知识库)
```http
POST /api/documents/upload
Content-Type: multipart/form-data

file: (binary)
```

### 3. 开始对话 (RAG)
```http
POST /api/chat
Content-Type: application/json

{
  "message": "项目里提到的 API Key 怎么生成？"
}
```
响应为 SSE (Server-Sent Events) 流式输出。

### 4. 管理 API Key
```http
POST /api/keys
Content-Type: application/json

{
  "role": "user",
  "label": "前端应用"
}
```

## 💻 本地开发

如果你想在本地直接运行代码（不使用 Docker）：

### 1. 环境准备
建议使用 Python 3.11+。

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 启动服务
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 运行测试
```bash
pytest
```

## 📂 项目结构

```
.
├── app/
│   ├── api/            # API 路由定义
│   ├── core/           # 核心配置与认证
│   ├── services/       # 业务逻辑 (RAG, KeyStore)
│   └── utils/          # 工具函数
├── data/               # 存放 API Key 数据 (需持久化)
├── chroma_db/          # 存放向量数据库 (需持久化)
├── docker-compose.yml  # 容器编排
├── Dockerfile          # 镜像构建
└── requirements.txt    # Python 依赖
```
