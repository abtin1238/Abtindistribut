FROM node:20-alpine AS fe
WORKDIR /fe
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /srv/app
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core curl && rm -rf /var/lib/apt/lists/* \
 && useradd --system --uid 10001 --home /srv/app abtin
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=abtin:abtin . .
COPY --from=fe --chown=abtin:abtin /fe/dist /srv/app/frontend/dist
RUN mkdir -p /srv/app/uploads && chown -R abtin:abtin /srv/app/uploads
ENV DATABASE_URL=postgresql+psycopg://abtin:abtin@db:5432/abtin_distribution \
    PYTHONUNBUFFERED=1
USER abtin
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/ready" || exit 1
CMD ["sh","run.sh"]
