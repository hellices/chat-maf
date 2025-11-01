# Multi-stage build for chat-maf application
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install frontend dependencies
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Set environment variables for build
# PUBLIC_API_BASE_URL is set to empty string so frontend uses relative URLs
ENV PUBLIC_API_BASE_URL=""
ENV PUBLIC_OTLP_ENABLED="false"
ENV PUBLIC_OTLP_ENDPOINT=""

# Build frontend
RUN npm run build

# Stage 2: Setup backend with frontend static files
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies required for Python packages and Playwright
RUN apt-get update && apt-get install -y \
    curl \
    # Playwright dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy only pyproject.toml first for better caching
COPY backend/pyproject.toml ./backend/

# Set working directory to backend
WORKDIR /app/backend

# Install Python dependencies directly with pip from pyproject.toml
RUN pip install --no-cache-dir .

# Install Playwright browsers
RUN playwright install chromium

# Copy rest of backend files
COPY backend/ ./

# Copy built frontend to backend static directory
COPY --from=frontend-builder /app/frontend/build /app/backend/static

# Expose port 80 instead of 8000 (container will serve HTTP on 80)
EXPOSE 80

# Run the application on port 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
