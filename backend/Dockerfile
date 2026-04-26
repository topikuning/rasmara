# syntax=docker/dockerfile:1.6
# Multi-stage Dockerfile RASMARA backend.
# Target 'dev'  -> hot reload (runserver), volume mounted source.
# Target 'prod' -> gunicorn, source di-bake ke image.

ARG PYTHON_VERSION=3.12-slim-bookworm

# ---------- base ----------
FROM python:${PYTHON_VERSION} AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Sistem dep:
# - libpq-dev untuk psycopg
# - WeasyPrint butuh: libpango, libcairo, libgdk-pixbuf, fonts
# - libxml2/libxslt utk lxml
# - tini sebagai init process
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libpangoft2-1.0-0 \
        libpango-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        libxml2-dev \
        libxslt1-dev \
        shared-mime-info \
        fonts-dejavu \
        fonts-liberation \
        fonts-noto-core \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies dulu (cache friendly)
COPY pyproject.toml requirements.txt* /app/
RUN pip install --upgrade pip wheel \
    && if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# ---------- dev ----------
FROM base AS dev
ENV DJANGO_DEBUG=1
COPY . /app
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------- prod ----------
FROM base AS prod
ENV DJANGO_DEBUG=0
COPY . /app
RUN python manage.py collectstatic --noinput || true
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["gunicorn", "rasmara.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "90", "--access-logfile", "-"]
