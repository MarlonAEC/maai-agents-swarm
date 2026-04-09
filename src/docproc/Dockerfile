FROM python:3.11-slim

WORKDIR /app

# System dependencies for Docling layout models and EasyOCR
# libgl1 is NOT needed because we use opencv-python-headless (Research Pitfall 1)
# libglib2.0-0 is needed for some image processing operations by opencv-python-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libxcb1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation (per CLAUDE.md: use uv, not pip)
RUN pip install --no-cache-dir uv

# Copy project metadata and install dependencies before copying application code
# so that the dependency layer is cached independently of source changes.
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

# Copy application code
COPY . .

# Create uploads directory (will be mounted as volume from the host)
RUN mkdir -p /app/uploads

# Create EasyOCR model cache directory (persisted via volume for faster restarts)
RUN mkdir -p /root/.EasyOCR

EXPOSE 8001

# Longer start-period than core-api (30s) because Docling + EasyOCR model loading
# is slow on first boot — both models are downloaded and cached on startup.
HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=120s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
