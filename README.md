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

访问 `http://127.0.0.1:8000` 或 `http://127.0.0.1:8000/health`。

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

# 运行容器
docker run -d -p 8000:8000 --name fastapi-app fastapi-starter
```
访问 `http://127.0.0.1:8000` 或 `/health`。`.dockerignore` 已排除 `.venv` 等本地文件，减少镜像上下文体积。
