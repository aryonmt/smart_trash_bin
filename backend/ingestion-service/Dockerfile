# backend/ingestion-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the modular source package
COPY src/ ./src/

ENV PYTHONUNBUFFERED=1

# Execute module via python -m path to enable clean relative imports
CMD ["python", "-m", "src.main"]
