# Multi-stage production build for ORBIS (Cloud Run / Render compatible)
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

# Install minimal tools for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
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

# Cloud Run & Render inject dynamic $PORT (default 8080)
ENV PORT=8080
ENV ORBIS_OFFLINE_AUTH=1
ENV DB_NAME=app

EXPOSE 8080

# Start server
CMD ["sh", "-c", "cd /app/backend && uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}"]
