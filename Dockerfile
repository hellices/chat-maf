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

# Install system dependencies required for Python packages
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy backend files
COPY backend/ ./backend/

# Set working directory to backend
WORKDIR /app/backend

# Install Python dependencies using uv
RUN uv pip install --system -r <(uv pip compile pyproject.toml) || \
    uv pip install --system \
    "agent-framework>=1.0.0b251016" \
    "fastapi[standard]>=0.119.0" \
    "uvicorn>=0.37.0" \
    "requests>=2.31.0" \
    "beautifulsoup4>=4.12.0" \
    "markdownify>=0.11.6" \
    "playwright>=1.40.0" \
    "python-dotenv>=1.1.1" \
    "nltk>=3.9.2"

# Install Playwright browsers
RUN playwright install chromium && \
    playwright install-deps chromium

# Copy built frontend to backend static directory
COPY --from=frontend-builder /app/frontend/build /app/backend/static

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
