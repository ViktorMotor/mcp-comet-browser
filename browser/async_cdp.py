"""Async wrapper for Chrome DevTools Protocol calls"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional
from threading import Lock
from mcp.logging_config import get_logger
from mcp.errors import CDPTimeoutError, CDPError

logger = get_logger("browser.async_cdp")


class AsyncCDP:
    """Async wrapper for synchronous pychrome CDP calls

    Provides:
    - Thread-safe CDP calls via executor
    - Configurable timeouts
    - Proper error handling with typed exceptions
    """

    def __init__(self, tab, timeout: float = 30.0):
        """Initialize AsyncCDP wrapper

        Args:
            tab: pychrome Tab instance
            timeout: Default timeout for CDP calls in seconds
        """
        self.tab = tab
        self.timeout = timeout
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cdp-")
        self._lock = Lock()

    async def evaluate(self, expression: str, returnByValue: bool = False,
                      timeout: Optional[float] = None) -> Dict[str, Any]:
        """Execute JavaScript in the browser

        Args:
            expression: JavaScript code to execute
            returnByValue: Whether to return the value directly
            timeout: Override default timeout

        Returns:
            CDP response dict with 'result' key

        Raises:
            CDPTimeoutError: If execution exceeds timeout
            CDPError: If CDP call fails
        """
        return await self._call_cdp(
            "Runtime.evaluate",
            expression=expression,
            returnByValue=returnByValue,
            timeout=timeout
        )

    async def query_selector(self, selector: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Query DOM for element matching selector

        Args:
            selector: CSS selector
            timeout: Override default timeout

        Returns:
            CDP response with nodeId

        Raises:
            CDPTimeoutError: If query exceeds timeout
            CDPError: If selector is invalid or element not found
        """
        # First get document
        doc = await self._call_cdp("DOM.getDocument", timeout=timeout)
        root_node_id = doc.get("root", {}).get("nodeId")

        if not root_node_id:
            raise CDPError("Failed to get document root")

        # Then query selector
        return await self._call_cdp(
            "DOM.querySelector",
            nodeId=root_node_id,
            selector=selector,
            timeout=timeout
        )

    async def query_selector_all(self, selector: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Query DOM for all elements matching selector

        Args:
            selector: CSS selector
            timeout: Override default timeout

        Returns:
            CDP response with nodeIds array

        Raises:
            CDPTimeoutError: If query exceeds timeout
            CDPError: If selector is invalid
        """
        # First get document
        doc = await self._call_cdp("DOM.getDocument", timeout=timeout)
        root_node_id = doc.get("root", {}).get("nodeId")

        if not root_node_id:
            raise CDPError("Failed to get document root")

        # Then query all
        return await self._call_cdp(
            "DOM.querySelectorAll",
            nodeId=root_node_id,
            selector=selector,
            timeout=timeout
        )

    async def get_outer_html(self, node_id: int, timeout: Optional[float] = None) -> str:
        """Get outer HTML of a DOM node

        Args:
            node_id: CDP node ID
            timeout: Override default timeout

        Returns:
            HTML string

        Raises:
            CDPTimeoutError: If call exceeds timeout
            CDPError: If node not found
        """
        result = await self._call_cdp(
            "DOM.getOuterHTML",
            nodeId=node_id,
            timeout=timeout
        )
        return result.get("outerHTML", "")

    async def capture_screenshot(self, format: str = "png", quality: Optional[int] = None,
                                timeout: Optional[float] = None) -> Dict[str, Any]:
        """Capture page screenshot

        Args:
            format: Image format (png or jpeg)
            quality: JPEG quality (0-100), only for jpeg
            timeout: Override default timeout

        Returns:
            CDP response with 'data' (base64 image)

        Raises:
            CDPTimeoutError: If capture exceeds timeout
            CDPError: If capture fails
        """
        kwargs = {"format": format}
        if quality is not None and format == "jpeg":
            kwargs["quality"] = quality

        return await self._call_cdp("Page.captureScreenshot", timeout=timeout, **kwargs)

    async def navigate(self, url: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Navigate to URL

        Args:
            url: URL to navigate to
            timeout: Override default timeout

        Returns:
            CDP response with frameId

        Raises:
            CDPTimeoutError: If navigation exceeds timeout
            CDPError: If navigation fails
        """
        return await self._call_cdp("Page.navigate", url=url, timeout=timeout)

    async def call_function_on(self, object_id: str, function_declaration: str,
                              arguments: Optional[list] = None,
                              timeout: Optional[float] = None) -> Dict[str, Any]:
        """Call function on remote object

        Args:
            object_id: Remote object ID
            function_declaration: Function body to execute
            arguments: Function arguments
            timeout: Override default timeout

        Returns:
            CDP response

        Raises:
            CDPTimeoutError: If call exceeds timeout
            CDPError: If call fails
        """
        kwargs = {
            "objectId": object_id,
            "functionDeclaration": function_declaration
        }
        if arguments:
            kwargs["arguments"] = arguments

        return await self._call_cdp("Runtime.callFunctionOn", timeout=timeout, **kwargs)

    async def _call_cdp(self, method: str, timeout: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        """Execute CDP method call with timeout and thread-safety

        Args:
            method: CDP method (e.g., "Runtime.evaluate")
            timeout: Override default timeout
            **kwargs: Method-specific parameters

        Returns:
            CDP response dict

        Raises:
            CDPTimeoutError: If execution exceeds timeout
            CDPError: If CDP call fails
        """
        timeout = timeout or self.timeout

        def _sync_call():
            """Synchronous CDP call in thread"""
            with self._lock:
                try:
                    # Parse method into domain and command
                    domain, command = method.split(".", 1)

                    # Get domain object and call method
                    domain_obj = getattr(self.tab, domain)
                    method_fn = getattr(domain_obj, command)

                    result = method_fn(**kwargs)
                    logger.debug(f"CDP call succeeded: {method}")
                    return result

                except AttributeError as e:
                    raise CDPError(f"Invalid CDP method: {method}") from e
                except Exception as e:
                    raise CDPError(f"CDP call failed: {method}: {str(e)}") from e

        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(self._executor, _sync_call),
                timeout=timeout
            )
            return result

        except asyncio.TimeoutError:
            logger.error(f"CDP call timeout: {method} (timeout={timeout}s)")
            raise CDPTimeoutError(
                f"CDP call timeout: {method}",
                method=method,
                timeout=timeout
            )
        except CDPError:
            # Re-raise typed CDP errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in CDP call: {method}: {e}")
            raise CDPError(f"CDP call failed: {method}: {str(e)}")

    async def close(self):
        """Shutdown executor"""
        logger.debug("Shutting down AsyncCDP executor")
        self._executor.shutdown(wait=True)
