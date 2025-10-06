#!/bin/bash
# Test MCP server via JSON-RPC

echo "Starting MCP server test..."
echo ""

# Start server in background
python3 server.py &
SERVER_PID=$!

sleep 2

echo "Test 1: List tools"
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | python3 server.py &
sleep 1

echo ""
echo "Test 2: Open URL"
echo '{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "open_url", "arguments": {"url": "https://example.com"}}}' | timeout 10 python3 server.py

echo ""
echo "Cleaning up..."
kill $SERVER_PID 2>/dev/null

echo "Test complete!"
