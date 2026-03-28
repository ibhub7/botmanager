# ── Stage 1: builder ─────────────────────────
FROM python:3.12-slim AS builder

# Added backslashes (\) to connect these lines
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Final Image ──────────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /install /usr/local

COPY . .

# Ensure permissions and directories are set correctly
RUN mkdir -p sessions && \
    useradd -m botuser && \
    chown -R botuser:botuser /app

USER botuser

EXPOSE 8080

HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')" || exit 1

# Using -u for unbuffered logs (highly recommended for Telegram bots)
CMD ["python", "-u", "main.py"]