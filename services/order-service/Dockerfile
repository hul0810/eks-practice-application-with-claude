FROM python:3.12-slim

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8002

ENV APP_VERSION=v1
ENV APP_PORT=8002
ENV OTLP_ENDPOINT=http://localhost:4317
ENV PRODUCT_SERVICE_URL=http://localhost:8001

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT} --timeout-graceful-shutdown 30"]
