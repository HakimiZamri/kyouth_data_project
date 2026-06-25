FROM python:3.14-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY frontend/pyproject.toml frontend/uv.lock ./

# Install dependencies
RUN uv sync --no-dev

# Copy source code
COPY frontend/src/ ./src/

COPY .env.example .env.example

# Create static directory
RUN mkdir -p ./src/static

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run
CMD ["uv", "run", "python", "-m", "src.app"]