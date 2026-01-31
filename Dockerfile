FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    git \
    espeak \
    libespeak1 \
    espeak-ng \
    libespeak-ng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Copy application code
COPY . .

# Install Python dependencies (production only, no dev dependencies)
RUN pip install --no-cache-dir .

# Create uploads directory with proper permissions
RUN mkdir -p /app/uploads && chmod 777 /app/uploads

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run without reload for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]