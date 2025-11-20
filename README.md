# FastAPI Starter (venv + pip)

## 环境
```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> 每次“新开一个终端”想运行/调试前，都先执行 `.\.venv\Scripts\activate` 来启用虚拟环境，再运行后面的命令。

## 运行
```powershell
.\.venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 `http://127.0.0.1:8000` 或 `http://127.0.0.1:8000/health`。

## 测试
```powershell
.\.venv\Scripts\activate
pytest
```

## 生成环境（生产部署）提示
- 依然需要先激活虚拟环境：`.\.venv\Scripts\activate`
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
