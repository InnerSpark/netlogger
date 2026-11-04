# Stage 1: build the dashboard (Node version matches .nvmrc)
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: the logger
FROM python:3.11-slim

LABEL org.opencontainers.image.title="Net Logger" \
      org.opencontainers.image.description="Receive-only check-in logger for AllStar ham radio nets" \
      org.opencontainers.image.licenses="AGPL-3.0-only"

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 netlogger

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY netlogger/ ./netlogger/
COPY tools/ ./tools/
COPY --from=web /web/dist ./web/dist

# Database and the downloaded Whisper model live in /data (mount a volume there)
ENV DATA_DIR=/data \
    PYTHONUNBUFFERED=1
RUN mkdir -p /data && chown netlogger:netlogger /data
USER netlogger

EXPOSE 34001/udp 8080/tcp
CMD ["python3", "-m", "netlogger"]
