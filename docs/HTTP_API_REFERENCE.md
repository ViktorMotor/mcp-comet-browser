# HTTP API Reference

**Version:** 3.1.0
**Service:** MCP Comet Browser HTTP Wrapper
**Base URL:** `http://127.0.0.1:9223`

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Endpoints](#endpoints)
4. [WebSocket Protocol](#websocket-protocol)
5. [Error Handling](#error-handling)
6. [Examples](#examples)
7. [Client Libraries](#client-libraries)

---

## 🎯 Overview

The HTTP wrapper provides a multi-client interface to MCP Comet Browser, allowing multiple Claude Code instances (or any HTTP client) to control a single browser simultaneously.

**Key Features:**
- ✅ **Multi-client support** - Unlimited concurrent connections
- ✅ **Request multiplexing** - ID rewriting prevents collisions
- ✅ **WebSocket support** - Persistent connections for real-time communication
- ✅ **RESTful API** - Simple HTTP POST for one-off commands
- ✅ **Auto-generated docs** - Swagger UI at `/docs`
- ✅ **Health monitoring** - `/health` and `/stats` endpoints

---

## 🏗️ Architecture

```
┌─────────────────┐
│ Claude Code 1   │─┐
├─────────────────┤ │
│ Claude Code 2   │─┼──→ HTTP API (9223)
├─────────────────┤ │      │
│ Claude Code 3   │─┘      │
└─────────────────┘         ↓
                   ┌────────────────────┐
                   │ mcp_http_wrapper.py│
                   │   [FastAPI]        │
                   │ - Multiplexing     │
                   │ - ID Rewriting     │
                   │ - Shared Connection│
                   └────────┬───────────┘
                            │
                            ↓
                   ┌────────────────────┐
                   │ windows_proxy.py   │
                   │   [TCP Proxy]      │
                   │ - Port: 9224       │
                   └────────┬───────────┘
                            │
                            ↓
                   ┌────────────────────┐
                   │   Comet Browser    │
                   │   CDP Port: 9222   │
                   └────────────────────┘
```

**Port Assignment:**
- `9222` - Comet Browser CDP (localhost only)
- `9224` - windows_proxy.py (TCP forwarding)
- `9223` - mcp_http_wrapper.py (HTTP/WebSocket API)

---

## 📡 Endpoints

### GET `/`

Root endpoint - API information

**Response:**
```json
{
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
```

---

### GET `/health`

Health check endpoint

**Response:**
```json
{
  "status": "ok",
  "browser_connected": true,
  "total_clients": 3,
  "active_clients": 2,
  "total_requests": 150,
  "failed_requests": 2,
  "success_rate": "98.67%"
}
```

**Status Codes:**
- `200 OK` - Service healthy
- `503 Service Unavailable` - Browser disconnected or manager not initialized

---

### GET `/stats`

Detailed statistics

**Response:**
```json
{
  "connected": true,
  "total_clients": 3,
  "active_clients": ["abc123", "def456", "ghi789"],
  "total_requests": 150,
  "failed_requests": 2,
  "success_rate": 0.9867
}
```

---

### POST `/execute`

Execute MCP command (transient connection)

**Request Body:**
```json
{
  "method": "Page.navigate",
  "params": {
    "url": "https://example.com"
  },
  "id": 1
}
```

**Parameters:**
- `method` (required): CDP method name (e.g., "Page.navigate", "Runtime.evaluate")
- `params` (optional): Method parameters as object (default: `{}`)
- `id` (optional): Request ID (auto-generated if not provided)

**Response (Success):**
```json
{
  "id": 1,
  "result": {
    "frameId": "...",
    "loaderId": "..."
  },
  "error": null
}
```

**Response (Error):**
```json
{
  "id": 1,
  "result": null,
  "error": {
    "code": -32601,
    "message": "Method not found: Invalid.method"
  }
}
```

**Status Codes:**
- `200 OK` - Command executed (check `error` field for CDP errors)
- `500 Internal Server Error` - Execution failed
- `503 Service Unavailable` - Not connected to browser

**Notes:**
- Uses transient `http_client` ID
- Suitable for one-off commands
- No persistent state maintained

---

### WebSocket `/ws`

Persistent connection for real-time communication

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:9223/ws');
```

**Send Message:**
```json
{
  "method": "Page.navigate",
  "params": {
    "url": "https://example.com"
  },
  "id": 1
}
```

**Receive Response:**
```json
{
  "id": 1,
  "result": {
    "frameId": "...",
    "loaderId": "..."
  }
}
```

**Error Response:**
```json
{
  "id": 1,
  "error": {
    "code": -32600,
    "message": "Invalid request: missing method"
  }
}
```

**Connection Lifecycle:**
1. Client connects → server assigns unique `client_id`
2. Server logs: `WebSocket client connected: abc123`
3. Client sends commands → server routes to browser
4. Client disconnects → server cleans up: `WebSocket client disconnected: abc123`

**Notes:**
- Each WebSocket connection gets unique client ID
- Persistent state for duration of connection
- Automatically unregistered on disconnect

---

## 🔌 WebSocket Protocol

### Message Format

All messages follow JSON-RPC 2.0 structure:

**Request:**
```json
{
  "method": "string",     // Required: CDP method
  "params": {},           // Optional: method parameters
  "id": 1                 // Optional: request ID
}
```

**Success Response:**
```json
{
  "id": 1,                // Matches request ID
  "result": {}            // Command result
}
```

**Error Response:**
```json
{
  "id": 1,                // Matches request ID
  "error": {
    "code": -32000,       // Error code
    "message": "string"   // Error description
  }
}
```

### Error Codes

| Code | Meaning |
|------|---------|
| `-32600` | Invalid Request (missing `method`) |
| `-32601` | Method Not Found |
| `-32000` | Server Error (generic) |

---

## 🚨 Error Handling

### HTTP Errors

**503 Service Unavailable:**
```json
{
  "detail": "Browser manager not initialized"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Tab has been stopped"
}
```

### CDP Errors

CDP errors are returned in the `error` field with HTTP 200:

```json
{
  "id": 1,
  "result": null,
  "error": {
    "code": -32601,
    "message": "Method not found: Invalid.method"
  }
}
```

**Common CDP Errors:**
- `Method not found` - Invalid CDP method
- `Invalid parameters` - Wrong parameter types
- `No target with given id` - Tab closed or invalid

---

## 💡 Examples

### Example 1: Navigate to URL (HTTP)

```bash
curl -X POST http://localhost:9223/execute \
  -H "Content-Type: application/json" \
  -d '{
    "method": "Page.navigate",
    "params": {"url": "https://example.com"},
    "id": 1
  }'
```

**Response:**
```json
{
  "id": 1,
  "result": {
    "frameId": "7A8...",
    "loaderId": "3F2..."
  }
}
```

---

### Example 2: Evaluate JavaScript (HTTP)

```bash
curl -X POST http://localhost:9223/execute \
  -H "Content-Type: application/json" \
  -d '{
    "method": "Runtime.evaluate",
    "params": {
      "expression": "document.title",
      "returnByValue": true
    },
    "id": 2
  }'
```

**Response:**
```json
{
  "id": 2,
  "result": {
    "result": {
      "type": "string",
      "value": "Example Domain"
    }
  }
}
```

---

### Example 3: WebSocket Connection (Python)

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:9223/ws"

    async with websockets.connect(uri) as websocket:
        # Send command
        await websocket.send(json.dumps({
            "method": "Page.navigate",
            "params": {"url": "https://example.com"},
            "id": 1
        }))

        # Receive response
        response = await websocket.recv()
        print(json.loads(response))

asyncio.run(test_websocket())
```

---

### Example 4: Multiple Clients (Bash)

```bash
# Terminal 1
curl -X POST http://localhost:9223/execute \
  -H "Content-Type: application/json" \
  -d '{"method": "Page.navigate", "params": {"url": "https://google.com"}, "id": 1}'

# Terminal 2 (simultaneously!)
curl -X POST http://localhost:9223/execute \
  -H "Content-Type: application/json" \
  -d '{"method": "Page.navigate", "params": {"url": "https://example.com"}, "id": 2}'
```

Both commands execute without collision due to ID rewriting.

---

### Example 5: Health Monitoring

```bash
# Check health
curl http://localhost:9223/health

# Get detailed stats
curl http://localhost:9223/stats

# Monitor in real-time (Linux/macOS)
watch -n 1 'curl -s http://localhost:9223/stats | jq'
```

---

## 📚 Client Libraries

### Python

```python
import aiohttp
import asyncio

class MCPClient:
    def __init__(self, base_url="http://localhost:9223"):
        self.base_url = base_url
        self.request_id = 0

    async def execute(self, method: str, params: dict = None):
        self.request_id += 1

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/execute",
                json={
                    "method": method,
                    "params": params or {},
                    "id": self.request_id
                }
            ) as response:
                return await response.json()

# Usage
async def main():
    client = MCPClient()
    result = await client.execute("Page.navigate", {"url": "https://example.com"})
    print(result)

asyncio.run(main())
```

---

### JavaScript/Node.js

```javascript
const axios = require('axios');

class MCPClient {
  constructor(baseURL = 'http://localhost:9223') {
    this.baseURL = baseURL;
    this.requestId = 0;
  }

  async execute(method, params = {}) {
    this.requestId++;

    const response = await axios.post(`${this.baseURL}/execute`, {
      method,
      params,
      id: this.requestId
    });

    return response.data;
  }
}

// Usage
(async () => {
  const client = new MCPClient();
  const result = await client.execute('Page.navigate', {
    url: 'https://example.com'
  });
  console.log(result);
})();
```

---

### cURL Script (Bash)

```bash
#!/bin/bash

MCP_BASE_URL="http://localhost:9223"
REQUEST_ID=1

mcp_execute() {
  local method="$1"
  local params="$2"

  curl -X POST "${MCP_BASE_URL}/execute" \
    -H "Content-Type: application/json" \
    -d "{\"method\": \"${method}\", \"params\": ${params}, \"id\": ${REQUEST_ID}}"

  REQUEST_ID=$((REQUEST_ID + 1))
}

# Usage
mcp_execute "Page.navigate" '{"url": "https://example.com"}'
```

---

## 🔍 Debugging

### Enable Verbose Logging

```bash
# Set log level
export LOG_LEVEL=DEBUG

# Run wrapper
python mcp_http_wrapper.py
```

### Common Issues

**1. "Browser manager not initialized"**
- **Cause:** windows_proxy.py not running or Comet browser not started
- **Fix:** Start windows_proxy.py and ensure Comet is running with `--remote-debugging-port=9222`

**2. "Connection refused" on port 9223**
- **Cause:** mcp_http_wrapper.py not running
- **Fix:** `python mcp_http_wrapper.py`

**3. Slow response times**
- **Cause:** Request queueing (expected behavior for heavy operations)
- **Fix:** This is normal - requests execute sequentially for safety

---

## 📊 Performance Considerations

### Request Queuing

All requests execute sequentially to prevent race conditions. Expected behavior:
- Light operations: <100ms per request
- Heavy operations (navigation, large JS): 1-3s per request
- Multiple clients: requests queued in order received

### Connection Limits

- **HTTP clients:** Unlimited (each request creates transient connection)
- **WebSocket clients:** Unlimited (but recommended <10 for performance)
- **Browser connections:** 1 shared connection (multiplexed)

### Recommended Usage

- **One-off commands:** Use HTTP `/execute`
- **Interactive sessions:** Use WebSocket `/ws`
- **Monitoring:** Use HTTP `/health` and `/stats`

---

## 🔒 Security

### Bind Address

Default: `127.0.0.1` (localhost only)

**WARNING:** Only change if you understand security implications!

```bash
# .env file
MCP_HTTP_HOST=127.0.0.1  # Localhost only (safe)
# MCP_HTTP_HOST=0.0.0.0  # All interfaces (DANGEROUS!)
```

### Authentication

**Not implemented** - This service is designed for local development only.

**For production:**
- Use reverse proxy (nginx) with authentication
- Use VPN or SSH tunneling
- Never expose port 9223 to public internet

---

## 🛠️ Configuration

### Environment Variables

Create `.env` file:

```bash
# HTTP Wrapper Settings
MCP_HTTP_PORT=9223          # HTTP API port (default: 9223)
MCP_HTTP_HOST=127.0.0.1     # Bind address (default: 127.0.0.1)

# CDP Proxy Settings
CDP_PROXY_HOST=127.0.0.1    # windows_proxy.py host (default: 127.0.0.1)
CDP_PROXY_PORT=9224         # windows_proxy.py port (default: 9224)
```

### Custom Port

```bash
# Change HTTP API port
export MCP_HTTP_PORT=8080
python mcp_http_wrapper.py
```

---

## 📖 See Also

- [Multi-Client Quick Start Guide](MULTI_CLIENT_QUICK_START.md)
- [CDP Protocol Reference](https://chromedevtools.github.io/devtools-protocol/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Main README](../README.md)

---

**Version:** 3.1.0
**Last Updated:** 2025-11-12
**Support:** https://github.com/your-repo/mcp_comet_for_claude_code/issues
