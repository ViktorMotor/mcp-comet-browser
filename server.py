#!/usr/bin/env python3
"""
MCP Server for Comet Browser Control via Chrome DevTools Protocol
Compatible with Model Context Protocol (MCP) v0.3 draft

Modular architecture with command pattern for browser automation.
"""
import asyncio
from mcp.protocol import MCPJSONRPCServer


async def main():
    """Entry point for MCP Comet Server"""
    server = MCPJSONRPCServer()
    try:
        await server.run()
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
    finally:
        server.close()


if __name__ == '__main__':
    import sys
    asyncio.run(main())
