# Kavach backend: store + trust + api in one container (D-08). Only the api port is public; store and trust listen on localhost.
FROM python:3.12-slim
WORKDIR /srv
RUN pip install --no-cache-dir uv==0.10.7
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend ./backend
COPY infra/Procfile.prod infra/start.sh ./infra/
ENV PATH="/srv/.venv/bin:$PATH" PYTHONPATH=/srv/backend PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN useradd --create-home --uid 10001 app && chown -R app /srv
USER app
CMD ["sh", "infra/start.sh"]
