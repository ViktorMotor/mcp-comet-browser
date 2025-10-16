#!/usr/bin/env python3
"""
MCP Server for Comet Browser Control via Chrome DevTools Protocol
Compatible with Model Context Protocol (MCP) v0.3 draft

Modular architecture with command pattern for browser automation.
"""
import os
import sys
import asyncio

from __version__ import __version__, __release_date__

# Clear proxy environment variables for WSL→Windows connection
# External proxies don't work for localhost/Windows host connections
for var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
            'ALL_PROXY', 'all_proxy', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(var, None)

from mcp.protocol import MCPJSONRPCServer
from mcp.logging_config import get_logger

logger = get_logger("server")


async def main():
    """Entry point for MCP Comet Server"""
    logger.info(f"MCP Comet Browser v{__version__} ({__release_date__})")
    server = MCPJSONRPCServer()
    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        server.close()


if __name__ == '__main__':
    asyncio.run(main())
