# Multi-stage production build for ORBIS on Render
# Stage 1: Build the React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* frontend/yarn.lock* ./
RUN if [ -f package-lock.json ]; then npm ci --ignore-scripts; else npm install; fi

COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python runtime
FROM python:3.11-slim
WORKDIR /app

# Install minimal build tools and curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libtool \
    autoconf \
    automake \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend and scientific core
COPY ACI/ ./ACI/
COPY ml/ ./ml/
COPY backend/ ./backend/
COPY sp3_parser.py ./sp3_parser.py
COPY sp3_reference.csv ./sp3_reference.csv

# Copy built frontend assets from builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Render automatically provides $PORT
ENV PORT=10000
ENV ORBIS_OFFLINE_AUTH=1
ENV DB_NAME=app
ENV APP_URL=https://orbis-sda.onrender.com
ENV CORS_ORIGINS=https://orbis-sda.onrender.com

EXPOSE 10000

# Start server
CMD ["sh", "-c", "cd /app/backend && uvicorn server:app --host 0.0.0.0 --port ${PORT:-10000}"]
