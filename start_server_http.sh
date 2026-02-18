#!/bin/bash
# PM-MCP HTTP SSE Server Startup Script for Claude.ai integration

echo "🚀 Starting PM-MCP HTTP SSE Server..."
cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run server in HTTP SSE mode
echo "📡 Server will be available at http://0.0.0.0:8010"
python -m uvicorn mcp_server.mcp_app_http:app --host 0.0.0.0 --port 8010 --reload

echo "✅ PM-MCP HTTP Server started"
