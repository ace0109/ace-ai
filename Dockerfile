FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝代码
COPY app app

EXPOSE 8000

# 生产运行命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
