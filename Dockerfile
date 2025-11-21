FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝代码（不带本地数据）
COPY app app

# 预创建运行时目录，避免容器内缺少 data/chroma_db 导致的写入问题
RUN mkdir -p /app/data /app/chroma_db

EXPOSE 8000

# 生产运行命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
