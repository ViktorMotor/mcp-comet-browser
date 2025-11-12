"""Shared Browser Connection Manager for Multi-Client Support

Manages single CDP connection shared by multiple MCP clients.
Implements request multiplexing with ID rewriting.

Version: 3.1.0 (FINAL)
"""
import asyncio
import uuid
import logging
from typing import Dict, Optional, Any, Callable
from datetime import datetime
import pychrome

logger = logging.getLogger(__name__)


class SharedBrowserConnection:
    """Manages shared browser connection for multiple clients"""

    def __init__(self, host: str = "127.0.0.1", port: int = 9224):
        """
        Initialize shared connection manager

        Args:
            host: CDP proxy host (windows_proxy.py)
            port: CDP proxy port (default: 9224)
        """
        self.host = host
        self.port = port
        self.browser: Optional[pychrome.Browser] = None
        self.tab: Optional[Any] = None

        # Client management
        self.clients: Dict[str, Dict[str, Any]] = {}  # client_id -> metadata
        self.active_requests: Dict[str, str] = {}  # rewritten_id -> original_client_id

        # Request routing
        self.pending_responses: Dict[str, asyncio.Future] = {}  # rewritten_id -> Future

        # Connection state
        self.connected = False
        self.reconnecting = False

        # Stats
        self.total_requests = 0
        self.failed_requests = 0

        logger.info(f"ConnectionManager initialized (target: {host}:{port})")

    async def connect(self) -> bool:
        """Connect to browser via CDP proxy"""
        try:
            logger.info(f"Connecting to browser at {self.host}:{self.port}...")

            # Connect to browser
            self.browser = pychrome.Browser(url=f"http://{self.host}:{self.port}")

            # Get or create tab
            tabs = self.browser.list_tab()
            if tabs:
                self.tab = tabs[0]
                logger.info(f"Using existing tab: {self.tab.id}")
            else:
                self.tab = self.browser.new_tab()
                logger.info(f"Created new tab: {self.tab.id}")

            # Start tab
            self.tab.start()

            # Enable CDP domains
            await self._enable_cdp_domains()

            self.connected = True
            logger.info("✓ Browser connection established")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to browser: {e}")
            self.connected = False
            return False

    async def _enable_cdp_domains(self):
        """Enable required CDP domains"""
        try:
            self.tab.Page.enable()
            self.tab.Runtime.enable()
            self.tab.DOM.enable()
            self.tab.Console.enable()
            logger.debug("CDP domains enabled")
        except Exception as e:
            logger.warning(f"Failed to enable some CDP domains: {e}")

    async def disconnect(self):
        """Disconnect from browser"""
        try:
            if self.tab:
                self.tab.stop()
            if self.browser:
                pass  # pychrome Browser doesn't have close()

            self.connected = False
            logger.info("Browser connection closed")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    def register_client(self, client_id: Optional[str] = None) -> str:
        """
        Register new client connection

        Args:
            client_id: Optional custom client ID

        Returns:
            Client ID (generated if not provided)
        """
        if not client_id:
            client_id = str(uuid.uuid4())[:8]

        self.clients[client_id] = {
            "connected_at": datetime.now().isoformat(),
            "requests": 0,
            "last_request": None
        }

        logger.info(f"Client registered: {client_id} (total: {len(self.clients)})")
        return client_id

    def unregister_client(self, client_id: str):
        """Unregister client connection"""
        if client_id in self.clients:
            stats = self.clients.pop(client_id)
            logger.info(f"Client unregistered: {client_id} (requests: {stats['requests']})")
        else:
            logger.warning(f"Attempted to unregister unknown client: {client_id}")

    def _rewrite_id(self, client_id: str, original_id: Any) -> str:
        """
        Rewrite request ID to avoid collisions

        Args:
            client_id: Client identifier
            original_id: Original request ID from client

        Returns:
            Rewritten unique ID
        """
        rewritten_id = f"{client_id}_{original_id}"
        self.active_requests[rewritten_id] = client_id
        return rewritten_id

    def _restore_id(self, rewritten_id: str) -> tuple[Optional[str], Optional[Any]]:
        """
        Restore original ID from rewritten ID

        Args:
            rewritten_id: Rewritten ID

        Returns:
            (client_id, original_id) tuple or (None, None)
        """
        if "_" not in rewritten_id:
            return None, None

        parts = rewritten_id.split("_", 1)
        if len(parts) != 2:
            return None, None

        client_id, original_id = parts

        # Try to convert original_id back to int if possible
        try:
            original_id = int(original_id)
        except (ValueError, TypeError):
            pass

        return client_id, original_id

    async def execute(self, client_id: str, method: str, params: Dict[str, Any], request_id: Optional[Any] = None) -> Dict[str, Any]:
        """
        Execute CDP command on behalf of client

        Args:
            client_id: Client making the request
            method: CDP method (e.g., "Runtime.evaluate")
            params: Method parameters
            request_id: Original request ID from client

        Returns:
            CDP response (with original ID restored)
        """
        if not self.connected:
            raise RuntimeError("Not connected to browser")

        # Update client stats
        if client_id in self.clients:
            self.clients[client_id]["requests"] += 1
            self.clients[client_id]["last_request"] = datetime.now().isoformat()

        self.total_requests += 1

        # Generate request ID if not provided
        if request_id is None:
            request_id = self.total_requests

        # Rewrite ID
        rewritten_id = self._rewrite_id(client_id, request_id)

        try:
            logger.debug(f"[{client_id}] Executing: {method} (id: {request_id} → {rewritten_id})")

            # Execute CDP command
            # Note: pychrome doesn't support custom IDs directly, so we'll use eval
            # For production, we'd implement custom WebSocket handling

            # For now, execute synchronously (TODO: async with custom IDs)
            method_parts = method.split(".")
            if len(method_parts) == 2:
                domain, command = method_parts
                domain_obj = getattr(self.tab, domain, None)
                if domain_obj:
                    command_func = getattr(domain_obj, command, None)
                    if command_func:
                        result = command_func(**params)

                        return {
                            "id": request_id,  # Restore original ID
                            "result": result
                        }

            # Fallback: method not found
            return {
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

        except Exception as e:
            logger.error(f"[{client_id}] Command failed: {method} - {e}")
            self.failed_requests += 1

            return {
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics"""
        return {
            "connected": self.connected,
            "total_clients": len(self.clients),
            "active_clients": list(self.clients.keys()),
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.total_requests - self.failed_requests) / self.total_requests if self.total_requests > 0 else 1.0
        }

    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client information"""
        return self.clients.get(client_id)
