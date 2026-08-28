FROM python:3.12-slim

WORKDIR /app

# Keep the venv outside /app: docker-compose bind-mounts the host project
# over /app for live-reload dev, which would otherwise hide the venv built
# below (see week-01/docker/notes/01-docker-essentials.md#4).
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# Copy dependency files first so this layer only reruns when deps actually
# change, not on every code edit (see week-01/docker/notes/01-docker-essentials.md#3).
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
