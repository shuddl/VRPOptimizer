# scripts/start_api.sh
#!/bin/bash

# API server startup script
set -e

# Activate virtual environment
source venv/bin/activate

# Load environment variables
set -a
source .env
set +a

echo "🚀 Starting API server..."

# Check if port is specified
PORT=${1:-8000}

# Start API server with Uvicorn
exec uvicorn src.api.routes:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers 4 \
    --log-level info \
    --reload \
    --proxy-headers \
    --forwarded-allow-ips='*'
