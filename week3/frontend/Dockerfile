FROM python:3.14.5-bookworm 

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
 
WORKDIR /app
 
# Copy dependency files first for better layer caching
COPY pyproject.toml ./
 
# Install dependencies
RUN uv sync --no-dev || uv pip install --system fastapi "uvicorn[standard]" jinja2
 
# Copy source code
COPY src ./src
 
EXPOSE 8000

ENTRYPOINT ["uv", "run", "uvicorn"]
CMD ["--app-dir", "src", "--host", "0.0.0.0", "app:app"] 