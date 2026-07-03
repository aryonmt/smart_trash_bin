# backend/fill-estimation-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the core domain logic directory and the main runner
COPY domain/ ./domain/
COPY main.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
