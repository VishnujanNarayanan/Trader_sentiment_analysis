# Runs the analysis anywhere, with the versions it was developed against.
FROM python:3.12-slim

WORKDIR /app

# Dependencies first, so a code edit does not invalidate the pip layer.
COPY requirements.txt requirements-dev.txt requirements-app.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt -r requirements-app.txt

COPY src/ ./src/
COPY sql/ ./sql/
COPY tests/ ./tests/
COPY .streamlit/ ./.streamlit/
COPY pyproject.toml app.py ./

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    TS_DATA_DIR=/data \
    TS_DB_PATH=/data/trader_sentiment.db

# The trade export is 47MB and is mounted at run time rather than baked in.
# The Fear & Greed index is fetched from its public API on first run and cached
# into the same volume.
VOLUME ["/data"]

# The app is served from this image too, which is why streamlit and app.py are
# both here:
#   docker run --rm -p 8501:8501 trader-sentiment \
#     streamlit run app.py --server.address 0.0.0.0
EXPOSE 8501

CMD ["python", "-m", "trader_sentiment.build"]
