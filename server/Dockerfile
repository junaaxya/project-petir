FROM python:3.12-slim

WORKDIR /app

COPY packages/contracts /app/packages/contracts
COPY server /app/server

RUN pip install --no-cache-dir -e /app/packages/contracts -e "/app/server" \
    && pip install --no-cache-dir uvicorn

WORKDIR /app/server

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
