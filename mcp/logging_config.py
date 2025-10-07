"""
Structured logging configuration for MCP Comet Browser.

Provides unified logging interface with:
- Consistent format: [TIMESTAMP] LEVEL [module] message
- Environment-based log level: MCP_LOG_LEVEL
- All logs to stderr (stdout reserved for JSON-RPC)
"""

import logging
import sys
import os


class StderrOnlyHandler(logging.StreamHandler):
    """Handler that ensures all logs go to stderr only."""

    def __init__(self):
        super().__init__(stream=sys.stderr)


def setup_logging(name: str = "mcp_comet") -> logging.Logger:
    """
    Setup structured logging for MCP server.

    Args:
        name: Logger name (typically module name)

    Returns:
        Configured logger instance

    Environment Variables:
        MCP_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
                      Default: INFO
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Get log level from environment
    log_level_str = os.environ.get("MCP_LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    logger.setLevel(log_level)

    # Create stderr handler
    handler = StderrOnlyHandler()
    handler.setLevel(log_level)

    # Format: [TIMESTAMP] LEVEL [module] message
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


# Convenience function for getting module-specific loggers
def get_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        module_name: Name of the module (e.g., "mcp.protocol", "commands.click")

    Returns:
        Logger configured with module name

    Example:
        logger = get_logger(__name__)
        logger.info("Server started")
    """
    return setup_logging(f"mcp_comet.{module_name}")
