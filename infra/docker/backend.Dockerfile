# 旅行助手 后端 Docker 镜像
FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend /app/backend
COPY data /app/data
COPY storage /app/storage
ENV PYTHONPATH=/app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
