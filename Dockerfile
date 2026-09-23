# Production image for ORBIS Space Domain Awareness Platform
FROM python:3.11-slim
WORKDIR /app

# Install curl for health checks
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
COPY IGS0OPSFIN_20260910000_01D_15M_ORB.SP3* ./

# Copy pre-compiled production frontend SPA
COPY frontend/dist ./frontend/dist

# Render & Cloud Run dynamic $PORT (Render default is 10000)
ENV PORT=10000
ENV ORBIS_OFFLINE_AUTH=1
ENV DB_NAME=app

EXPOSE 10000

# Start server
CMD ["sh", "-c", "cd /app/backend && uvicorn server:app --host 0.0.0.0 --port ${PORT:-10000}"]
