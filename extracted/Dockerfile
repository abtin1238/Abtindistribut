FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NPM_CONFIG_UPDATE_NOTIFIER=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python3 -m pip install --break-system-packages -r /app/backend/requirements.txt

COPY frontend/package*.json /app/frontend/
RUN cd /app/frontend && npm ci --no-audit --no-fund

COPY . /app

RUN chmod +x /app/render-start.sh

EXPOSE 10000

CMD ["/app/render-start.sh"]
