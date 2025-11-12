"""MCP Comet Browser HTTP Wrapper - Multi-Client Support

HTTP/WebSocket wrapper for MCP Comet Browser supporting multiple Claude Code instances.

Usage:
    python mcp_http_wrapper.py

Environment Variables:
    MCP_HTTP_PORT=9223          # HTTP API port (default: 9223)
    MCP_HTTP_HOST=127.0.0.1     # Bind address (default: 127.0.0.1)
    CDP_PROXY_HOST=127.0.0.1    # windows_proxy.py host (default: 127.0.0.1)
    CDP_PROXY_PORT=9224         # windows_proxy.py port (default: 9224)

Version: 3.1.0 (FINAL)
"""
import sys
import os
from pathlib import Path

# Add project root to Python path (allows running from any directory)
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from mcp.connection_manager import SharedBrowserConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration from ENV
HTTP_HOST = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
HTTP_PORT = int(os.getenv("MCP_HTTP_PORT", "9223"))
CDP_PROXY_HOST = os.getenv("CDP_PROXY_HOST", "127.0.0.1")
CDP_PROXY_PORT = int(os.getenv("CDP_PROXY_PORT", "9224"))

# FastAPI app
app = FastAPI(
    title="MCP Comet Browser HTTP Wrapper",
    description="Multi-client HTTP/WebSocket wrapper for MCP Comet Browser",
    version="3.1.0"
)

# Global connection manager
browser_manager: Optional[SharedBrowserConnection] = None


# Pydantic models
class MCPRequest(BaseModel):
    """MCP command request"""
    method: str
    params: Dict[str, Any] = {}
    id: Optional[int] = None


class MCPResponse(BaseModel):
    """MCP command response"""
    id: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


@app.on_event("startup")
async def startup():
    """Initialize browser connection on startup"""
    global browser_manager

    logger.info("=== MCP HTTP Wrapper v3.1.0 Starting ===")
    logger.info(f"HTTP API: http://{HTTP_HOST}:{HTTP_PORT}")
    logger.info(f"CDP Proxy: {CDP_PROXY_HOST}:{CDP_PROXY_PORT}")

    # Create connection manager
    browser_manager = SharedBrowserConnection(
        host=CDP_PROXY_HOST,
        port=CDP_PROXY_PORT
    )

    # Connect to browser
    connected = await browser_manager.connect()
    if not connected:
        logger.error("❌ Failed to connect to browser!")
        logger.error("Make sure windows_proxy.py is running and Comet browser is open")
    else:
        logger.info("✅ Connected to browser successfully")

    logger.info("=== HTTP Wrapper Ready ===")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global browser_manager

    logger.info("Shutting down HTTP wrapper...")

    if browser_manager:
        await browser_manager.disconnect()

    logger.info("HTTP wrapper stopped")


@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "service": "MCP Comet Browser HTTP Wrapper",
        "version": "3.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "execute": "/execute (POST)",
            "websocket": "/ws",
            "stats": "/stats",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    if not browser_manager:
        raise HTTPException(status_code=503, detail="Browser manager not initialized")

    stats = browser_manager.get_stats()

    return {
        "status": "ok" if browser_manager.connected else "disconnected",
        "browser_connected": browser_manager.connected,
        "total_clients": stats["total_clients"],
        "active_clients": stats["active_clients"],
        "total_requests": stats["total_requests"],
        "failed_requests": stats["failed_requests"],
        "success_rate": f"{stats['success_rate']:.2%}"
    }


@app.get("/stats")
async def get_stats():
    """Get detailed statistics"""
    if not browser_manager:
        raise HTTPException(status_code=503, detail="Browser manager not initialized")

    return browser_manager.get_stats()


@app.post("/execute")
async def execute_command(request: MCPRequest):
    """Execute MCP command"""
    if not browser_manager:
        raise HTTPException(status_code=503, detail="Browser manager not initialized")

    if not browser_manager.connected:
        raise HTTPException(status_code=503, detail="Not connected to browser")

    # Generate client ID for HTTP requests (transient)
    client_id = "http_client"

    try:
        # Register client if not exists
        if client_id not in browser_manager.clients:
            browser_manager.register_client(client_id)

        # Execute command
        response = await browser_manager.execute(
            client_id=client_id,
            method=request.method,
            params=request.params,
            request_id=request.id
        )

        return MCPResponse(**response)

    except Exception as e:
        logger.error(f"Execute failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for persistent connections"""
    if not browser_manager:
        await websocket.close(code=1011, reason="Browser manager not initialized")
        return

    # Accept connection
    await websocket.accept()

    # Register client
    client_id = browser_manager.register_client()
    logger.info(f"WebSocket client connected: {client_id}")

    try:
        while True:
            # Receive JSON command
            data = await websocket.receive_json()

            # Validate request
            if "method" not in data:
                await websocket.send_json({
                    "error": {"code": -32600, "message": "Invalid request: missing method"}
                })
                continue

            # Execute command
            try:
                response = await browser_manager.execute(
                    client_id=client_id,
                    method=data["method"],
                    params=data.get("params", {}),
                    request_id=data.get("id")
                )

                # Send response
                await websocket.send_json(response)

            except Exception as e:
                logger.error(f"[{client_id}] Command execution failed: {e}")
                await websocket.send_json({
                    "id": data.get("id"),
                    "error": {
                        "code": -32000,
                        "message": str(e)
                    }
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        # Unregister client
        browser_manager.unregister_client(client_id)


def main():
    """Run HTTP wrapper server"""
    logger.info("Starting MCP HTTP Wrapper...")

    # Check if windows_proxy.py is likely running
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((CDP_PROXY_HOST, CDP_PROXY_PORT))
        sock.close()

        if result != 0:
            logger.warning("=" * 60)
            logger.warning("WARNING: Cannot connect to CDP proxy")
            logger.warning(f"Make sure windows_proxy.py is running on {CDP_PROXY_HOST}:{CDP_PROXY_PORT}")
            logger.warning("=" * 60)
    except Exception as e:
        logger.warning(f"Could not check CDP proxy: {e}")

    # Run uvicorn server
    uvicorn.run(
        app,
        host=HTTP_HOST,
        port=HTTP_PORT,
        log_level="info",
        access_log=False  # Reduce log noise
    )


if __name__ == "__main__":
    main()
