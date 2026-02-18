#!/bin/bash
# PM-MCP Server Startup Script

echo "🚀 Starting PM-MCP Server..."
cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Run server
python mcp_server/mcp_app.py

echo "✅ PM-MCP Server started on http://0.0.0.0:8010"
