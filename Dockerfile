FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[dev]"

COPY . .
RUN pip install --no-cache-dir -e ".[dev]"

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import artemis" || exit 1

CMD ["artemis", "--help"]
