# Use Python 3.11 slim base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for Playwright browsers
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only for smaller image size)
# Note: install-deps is not needed as we installed system deps manually above
RUN playwright install chromium && \
    playwright install-deps chromium || true

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/chroma_db /app/data/mutual_funds /app/data/downloaded_html && \
    chmod -R 755 /app

# Expose port (Railway will set PORT env variable)
EXPOSE 8000

# Set environment variables for Playwright and Railway
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# Health check (optional, Railway also has its own)
# Note: Railway's healthcheck in railway.json takes precedence
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
# Railway provides PORT environment variable, use it or default to 8000
# Using shell form to allow variable substitution
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

