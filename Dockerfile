# Runs the analysis anywhere, with the versions it was developed against.
FROM python:3.12-slim

WORKDIR /app

# Dependencies first, so a code edit does not invalidate the pip layer.
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY src/ ./src/
COPY sql/ ./sql/
COPY tests/ ./tests/
COPY pyproject.toml ./

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    TS_DATA_DIR=/data \
    TS_DB_PATH=/data/trader_sentiment.db

# The trade export is 47MB and is mounted at run time rather than baked in.
# The Fear & Greed index is fetched from its public API on first run and cached
# into the same volume.
VOLUME ["/data"]

CMD ["python", "-m", "trader_sentiment.build"]
