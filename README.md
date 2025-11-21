# FastAPI Starter (venv + pip)

## 环境

> ✅ 建议使用 **Python 3.11 ~ 3.12** 且 `pip >= 24.3`（部分依赖在 3.13 尚无预编译轮子，解析更慢）。

### Windows
```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> 如 `pip install -r requirements.txt` 长时间停留在 *dependency resolver*，先确认 pip 已升级，再重试或追加 `--use-feature=fast-deps` 以减少解析耗时。

> 每次“新开一个终端”想运行/调试前，都先执行激活命令（Windows: `.\.venv\Scripts\activate`, macOS/Linux: `source .venv/bin/activate`）来启用虚拟环境，再运行后面的命令。

### 依赖锁定（可选）
```bash
pip install pip-tools
pip-compile requirements.txt --output-file requirements.lock
pip install -r requirements.lock
```
> ⚠️ 在 Python 3.11/3.12 环境运行 `pip-compile`，以确保 `onnxruntime` 等依赖有可用的预编译包；3.13 上会因为缺少 wheel 直接失败。

## 项目结构（核心）
```
app/
  api/          # 业务接口路由
    routes.py
  core/         # 基础能力，如认证
    auth.py
  services/     # 服务层
    rag.py
  main.py       # FastAPI 入口
```

## API Key 认证
- 首次启动时会自动生成一个超级管理员 API Key，写入 `data/initial_superadmin_key.txt`（仅生成一次），用于管理和生成后续的 Key。
- 生成新的 API Key：使用超级管理员或管理员 Key 调用 `POST /api/keys`，传入 `{"role": "user" | "admin", "label": "可选备注"}`，响应会返回一次性的明文 `api_key`。
- 查询已有 Key（不含明文）：`GET /api/keys`（需要管理员/超级管理员权限）。
- 所有接口（包括 `/api/chat` 和其他 `/api/*`）均需在请求头携带 `X-API-Key: <有效密钥>` 进行认证。

## 运行

### Windows
```powershell
.\.venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### macOS / Linux
```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问时在请求头附带 `X-API-Key`，例如健康检查 `http://127.0.0.1:8000/api/health`、聊天接口 `http://127.0.0.1:8000/api/chat`。

## 测试

### Windows
```powershell
.\.venv\Scripts\activate
pytest
```

### macOS / Linux
```bash
source .venv/bin/activate
pytest
```

## 生成环境（生产部署）提示
- 依然需要先激活虚拟环境：Windows 使用 `.\.venv\Scripts\activate`，macOS/Linux 使用 `source .venv/bin/activate`
- 运行 Uvicorn（不加 `--reload`）：`uvicorn app.main:app --host 0.0.0.0 --port 8000`
- 部署到生产时，通常放在反向代理（如 Nginx）后面，并使用守护进程或进程管理器（如 systemd、supervisor）保持进程存活，或用 `gunicorn -k uvicorn.workers.UvicornWorker app.main:app`.

## Docker 部署
```powershell
# 生成镜像
docker build -t fastapi-starter .

# 运行容器（建议挂载运行时数据目录）
docker run -d -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/chroma_db:/app/chroma_db \
  --name fastapi-app fastapi-starter
```
说明：
- 默认镜像内会在 `/app/data` 存放 API Key 数据库（`api_keys.db`）及初始超管 Key 文件（首次写入），`/app/chroma_db` 存放向量库，建议挂载为本地目录以持久化。
- 如需自定义挂载路径，替换 `-v` 参数即可；若容器以非 root 运行，请确保挂载目录具备写权限。

访问时在请求头附带 `X-API-Key`，如 `/api/health`、`/api/chat`。`.dockerignore` 已排除 `.venv`、`data/`、`chroma_db/` 等本地文件，减少镜像上下文体积。
