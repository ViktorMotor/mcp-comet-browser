#!/usr/bin/env python3
"""Quick test for MCP server connection"""
import asyncio
from server import CometMCPServer

async def test():
    server = CometMCPServer()
    print(f"Connecting to browser at {server.debug_host}:{server.debug_port}...")
    await server.connect()
    print("✓ Connected successfully!")

    # Test open URL
    result = await server.open_url("https://example.com")
    print(f"✓ Open URL: {result}")

    # Test evaluate JS
    result = await server.evaluate_js("return document.title")
    print(f"✓ Evaluate JS: {result}")

    server.close()

if __name__ == '__main__':
    asyncio.run(test())
