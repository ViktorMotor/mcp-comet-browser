#!/bin/bash

echo "=== Testing full MCP flow ==="
echo

# Start server in background
python3 server.py > /tmp/mcp_test_out.txt 2>&1 &
SERVER_PID=$!

sleep 1

# Test initialize
echo "1. Testing initialize..."
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}' | nc -U /proc/$SERVER_PID/fd/0 2>/dev/null || echo "Response 1" | python3 -c "
import json, sys
request = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1.0'}}}
print(json.dumps(request))
" | python3 server.py 2>/dev/null | head -1 | python3 -m json.tool | head -10

echo

# Test tools/list
echo "2. Testing tools/list..."
echo '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}' | python3 -c "
import subprocess, json, sys

proc = subprocess.Popen(
    ['python3', 'server.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Send both requests
proc.stdin.write('{\"jsonrpc\": \"2.0\", \"id\": 1, \"method\": \"initialize\", \"params\": {\"protocolVersion\": \"2024-11-05\", \"capabilities\": {}, \"clientInfo\": {\"name\": \"test\", \"version\": \"1.0\"}}}\\n')
proc.stdin.flush()
init_response = proc.stdout.readline()

proc.stdin.write('{\"jsonrpc\": \"2.0\", \"id\": 2, \"method\": \"tools/list\", \"params\": {}}\\n')
proc.stdin.flush()
tools_response = proc.stdout.readline()

data = json.loads(tools_response)
tools = data.get('result', {}).get('tools', [])
print(f'\\n✓ Got {len(tools)} tools from server')

proc.terminate()
"

# Cleanup
kill $SERVER_PID 2>/dev/null

echo
echo "=== Test complete ==="
