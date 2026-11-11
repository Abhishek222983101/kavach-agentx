FROM python:3.12-slim
WORKDIR /srv
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app
ENV PATH="/srv/.venv/bin:$PATH" PYTHONUNBUFFERED=1
# Hosts like Render/Fly/Railway inject $PORT.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
