# Shared base: python deps + app code, no native extras
FROM python:3.12-slim AS base

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Default to running the Temporal worker; tvt.temporal.start submits runs out of band.
CMD ["python", "-m", "tvt.temporal.worker"]

# Main worker image: pango + fonts for weasyprint PDF rendering. Noto core +
# CJK cover nearly every script so translations render everywhere. No ffmpeg.
FROM base AS main
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 \
        fonts-dejavu-core fonts-noto-core fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Screenshot worker image: ffmpeg only, no PDF stack
FROM base AS screenshot
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
