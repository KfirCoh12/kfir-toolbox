FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    KFIR_TOOLBOX_REQUIRE_AUTH=1 \
    KFIR_TOOLBOX_DATA_DIR=/data

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 toolbox \
    && mkdir -p /data \
    && chown -R toolbox:toolbox /app /data

COPY --chown=toolbox:toolbox . .

USER toolbox

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3).read()" || exit 1

CMD ["sh", "-c", "streamlit run private_app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true"]
