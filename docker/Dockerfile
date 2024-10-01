FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.source=https://github.com/jblawatt/fsspec-browser
LABEL org.opencontainers.image.licenses=MIT

WORKDIR /app

COPY pyproject.toml /app
COPY uv.lock /app

RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
  uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"

COPY . /app
COPY docker/run.sh run.sh

CMD ["/app/run.sh"]
