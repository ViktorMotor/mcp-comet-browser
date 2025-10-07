#!/usr/bin/env python3
"""
MCP Server for Comet Browser Control via Chrome DevTools Protocol
Compatible with Model Context Protocol (MCP) v0.3 draft

Modular architecture with command pattern for browser automation.
"""
import sys
import asyncio
from mcp.protocol import MCPJSONRPCServer
from mcp.logging_config import get_logger

logger = get_logger("server")


async def main():
    """Entry point for MCP Comet Server"""
    server = MCPJSONRPCServer()
    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        server.close()


if __name__ == '__main__':
    asyncio.run(main())
