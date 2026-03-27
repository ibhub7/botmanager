# ── Stage 1: builder ─────────────────────────

FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends 
gcc 
libssl-dev 
python3-dev 
build-essential 
&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Fix pip + wheel issue

RUN pip install --upgrade pip setuptools wheel

# Install dependencies

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime ─────────────────────────

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends 
libssl3 
&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

RUN mkdir -p sessions

RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

EXPOSE 8080

HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')" || exit 1

CMD ["python", "-u", "main.py"]
