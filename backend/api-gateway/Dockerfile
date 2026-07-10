# backend/api-gateway/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the modular source package
COPY src/ ./src/

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Execute module via python -m path to enable relative sub-package imports
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
