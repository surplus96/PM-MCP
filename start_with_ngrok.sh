#!/bin/bash
# Start PM-MCP with ngrok tunnel

echo "🚀 Starting PM-MCP with ngrok tunnel..."
cd "$(dirname "$0")"

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed. Please run: bash setup_ngrok.sh"
    exit 1
fi

# Start MCP server in background
echo "📡 Starting MCP HTTP SSE server..."
source .venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start server in background
nohup python -m uvicorn mcp_server.mcp_app_http:app --host 0.0.0.0 --port 8010 > mcp_server.log 2>&1 &
SERVER_PID=$!
echo "✅ MCP Server started (PID: $SERVER_PID)"

# Wait for server to start
sleep 3

# Start ngrok tunnel
echo "🌐 Starting ngrok tunnel..."
echo ""
echo "=" * 60
ngrok http 8010

# When ngrok exits, kill the server
kill $SERVER_PID
echo "🛑 MCP Server stopped"
