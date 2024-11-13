# scripts/start_ui.sh
#!/bin/bash

# UI server startup script
set -e

# Activate virtual environment
source venv/bin/activate

# Load environment variables
set -a
source .env
set +a

echo "🚀 Starting UI server..."

# Check if port is specified
PORT=${1:-8501}

# Start Streamlit server
exec streamlit run \
    --server.port $PORT \
    --server.address 0.0.0.0 \
    --browser.serverAddress localhost \
    --browser.gatherUsageStats false \
    ui/streamlit_app.py

# Make scripts executable
chmod +x scripts/*.sh