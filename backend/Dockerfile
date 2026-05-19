FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for Docling (PDF rendering, image processing) and onnxruntime.
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      libgl1 \
      libglib2.0-0 \
      libsm6 \
      libxext6 \
      libxrender1 \
      poppler-utils \
      tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install uv (modern Python package manager).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

COPY pyproject.toml ./
RUN uv pip install --system -e .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
