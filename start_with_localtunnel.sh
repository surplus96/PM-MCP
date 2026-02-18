#!/bin/bash
# Start PM-MCP with localtunnel (no account required!)

echo "🚀 Starting PM-MCP with localtunnel..."
cd "$(dirname "$0")"

# Check if npm and localtunnel are installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Installing Node.js and npm..."
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

if ! command -v lt &> /dev/null; then
    echo "📦 Installing localtunnel globally..."
    sudo npm install -g localtunnel
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

# Start localtunnel
echo "🌐 Starting localtunnel..."
echo ""
echo "================================================================"
echo "🔗 Your public URL will be displayed below"
echo "================================================================"
echo ""
lt --port 8010

# When localtunnel exits, kill the server
kill $SERVER_PID
echo "🛑 MCP Server stopped"
