FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/pyproject.toml .
RUN pip install --no-cache-dir .

# Install Playwright and Chromium for scrapers
RUN pip install playwright && playwright install --with-deps chromium

COPY backend/src /app/src
ENV PYTHONPATH=/app/src

CMD ["celery", "-A", "solarpros.celery_app.app", "worker", "--loglevel=info"]
