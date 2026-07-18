FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    COOKDAY_MOCK_LLM=1 \
    COOKDAY_HOST=0.0.0.0 \
    PORT=8080

COPY pyproject.toml README.md LICENSE ./
COPY app ./app
COPY cookday_agent ./cookday_agent
COPY docs ./docs

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8080

# Cloud Run sets PORT; default 8080 for local docker
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
