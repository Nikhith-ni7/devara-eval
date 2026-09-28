FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 EVAL_HOSTED=1 PORT=10000
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY app/ ./app/
COPY data/ ./data/
COPY prompts/ ./prompts/
COPY scripts/serve.sh ./scripts/serve.sh
COPY --from=frontend /build/dist ./frontend/dist
RUN useradd --create-home --uid 10001 evaluator && mkdir /app/storage && chown evaluator:evaluator /app/storage
USER evaluator
EXPOSE 10000
CMD ["bash", "scripts/serve.sh"]
