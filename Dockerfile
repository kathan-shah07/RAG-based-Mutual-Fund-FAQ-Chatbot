# Use Python 3.11 slim base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright browsers
RUN apt-get update && apt-get install -y \
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

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only for smaller image size)
# Note: install-deps is not needed as we installed system deps manually above
RUN playwright install chromium

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/chroma_db /app/data/mutual_funds /app/data/downloaded_html

# Expose port (Railway will set PORT env variable)
EXPOSE 8000

# Set environment variable for Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Run the application
# Railway provides PORT environment variable, use it or default to 8000
# Using shell form to allow variable substitution
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

