FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/pyproject.toml .
RUN pip install --no-cache-dir .

COPY backend/src /app/src
ENV PYTHONPATH=/app/src

EXPOSE 8000
CMD ["uvicorn", "solarpros.main:app", "--host", "0.0.0.0", "--port", "8000"]
