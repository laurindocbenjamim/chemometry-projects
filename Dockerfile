# Use a secure, slim, offical Python base image
FROM python:3.12-slim-bookworm

# Set container environment configurations
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set running directory in the container
WORKDIR /app

# Create a non-root system user for security compliance
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Install minimal OS dependencies if needed (e.g. for building scientific C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements first to leverage Docker build cache
COPY requirements.txt .

# Install dependencies using pip caching to speed up iterative builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files to /app
COPY --chown=appuser:appgroup . .

# Change ownership of app directory to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to the secure non-root user
USER appuser

# Expose port 8000
EXPOSE 8000

# Configure a simple API healthcheck to monitor container status
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/docs || exit 1

# Launch the FastAPI server using Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
