FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency installation (per CLAUDE.md: use uv, not pip)
RUN pip install --no-cache-dir uv

# Copy project metadata and install dependencies before copying application code
# so that the dependency layer is cached independently of source changes.
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

# Copy application code
COPY . .

# Create uploads directory (bind-mounted as a volume in Docker Compose)
RUN mkdir -p /app/uploads

EXPOSE 8000

# Health check uses Python stdlib so no extra binary (curl/wget) is needed.
HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
