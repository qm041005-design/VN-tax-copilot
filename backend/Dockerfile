# Đóng gói backend thành container (docker-compose.yml gọi file này để build service `backend`)
FROM python:3.12-slim
WORKDIR /app
# Không sinh file .pyc, log ra ngay (không bị đệm) -> xem `docker logs` realtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app:/app/backend
# Copy requirements trước để Docker cache lớp cài thư viện (sửa code không phải cài lại)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend /app/backend
COPY ai_engine /app/ai_engine
COPY data_pipeline/parser /app/data_pipeline/parser
WORKDIR /app/backend
EXPOSE 8000
# 0.0.0.0 để truy cập được từ ngoài container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
