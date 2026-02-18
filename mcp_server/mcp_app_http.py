"""
PM-MCP HTTP SSE Server for Claude.ai integration

This module provides an HTTP Server-Sent Events (SSE) endpoint that allows
Claude.ai to connect to the local MCP server via a public URL (e.g., ngrok).
"""

from __future__ import annotations
import asyncio
from mcp_server.mcp_app import mcp

# FastMCP의 SSE app을 Starlette 앱으로 export
# sse_app() 메서드를 호출하여 Starlette 앱 인스턴스를 생성
app = mcp.sse_app()

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🚀 PM-MCP HTTP SSE Server")
    print("=" * 60)
    print("📡 Starting server on http://0.0.0.0:8010")
    print("🔗 Use ngrok or localtunnel to expose this to Claude.ai")
    print("   Example: ngrok http 8010")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8010, log_level="info")
