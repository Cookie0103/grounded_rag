FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv==0.11.7 && uv sync --locked --no-dev --no-cache
COPY mock_core ./mock_core

EXPOSE 8001
HEALTHCHECK --interval=5s --timeout=3s --start-period=20s --retries=10 \
    CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8001/health', timeout=2).close()"]
CMD ["python", "-m", "uvicorn", "mock_core.main:app", "--host", "0.0.0.0", "--port", "8001"]
