# Razorpay AI Risk Manager
# Production Docker image

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/         ./api/
COPY rzp/         ./rzp/
COPY audit/       ./audit/
COPY webhooks/    ./webhooks/
COPY coldstart/   ./coldstart/
COPY batch/       ./batch/
COPY mlops/       ./mlops/
COPY artifacts/   ./artifacts/

# Copy env example (actual .env mounted at runtime)
COPY .env.example .env.example

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]