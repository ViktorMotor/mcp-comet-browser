"""
Shared pytest fixtures and configuration
"""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from dataclasses import dataclass
from typing import Optional, Dict, Any


@pytest.fixture
def mock_tab():
    """Mock pychrome Tab object"""
    tab = Mock()

    # Mock CDP domains
    tab.Runtime = Mock()
    tab.Runtime.evaluate = AsyncMock(return_value={"result": {"value": "test"}})

    tab.Page = Mock()
    tab.Page.navigate = AsyncMock()
    tab.Page.captureScreenshot = AsyncMock(return_value={"data": "base64data"})

    tab.DOM = Mock()
    tab.DOM.getDocument = AsyncMock(return_value={"root": {"nodeId": 1}})
    tab.DOM.querySelector = AsyncMock(return_value={"nodeId": 2})

    tab.Network = Mock()
    tab.Network.enable = AsyncMock()

    tab.Console = Mock()
    tab.Console.enable = AsyncMock()

    tab.Debugger = Mock()
    tab.Debugger.enable = AsyncMock()

    return tab


@pytest.fixture
def mock_async_cdp(mock_tab):
    """Mock AsyncCDP wrapper"""
    from browser.async_cdp import AsyncCDP

    cdp = AsyncMock(spec=AsyncCDP)
    cdp.tab = mock_tab
    cdp.evaluate = AsyncMock(return_value={"result": {"value": "test"}})
    cdp.navigate = AsyncMock()
    cdp.query_selector = AsyncMock(return_value={"nodeId": 2})
    cdp.capture_screenshot = AsyncMock(return_value={"data": "base64data"})

    return cdp


@pytest.fixture
def mock_cursor():
    """Mock AICursor object"""
    cursor = Mock()
    cursor.initialize = AsyncMock()
    cursor.move = AsyncMock()
    cursor.click = AsyncMock()
    cursor.hide = AsyncMock()
    cursor.cdp = Mock()

    return cursor


@pytest.fixture
def mock_browser():
    """Mock BrowserConnection object"""
    browser = Mock()
    browser.ensure_connected = AsyncMock()
    browser.get_tab = Mock()
    browser.console_logs = []
    browser.host = "localhost"
    browser.debug_port = 9222

    return browser


@pytest.fixture
def command_context(mock_tab, mock_cursor, mock_browser, mock_async_cdp):
    """Create CommandContext with mocks"""
    from commands.context import CommandContext

    return CommandContext(
        tab=mock_tab,
        cursor=mock_cursor,
        browser=mock_browser,
        cdp=mock_async_cdp
    )


@pytest.fixture
def sample_console_logs():
    """Sample console log data"""
    return [
        {
            "level": "log",
            "timestamp": 1234567890,
            "args": ["Test message"],
            "stackTrace": None
        },
        {
            "level": "error",
            "timestamp": 1234567891,
            "args": ["Error occurred"],
            "stackTrace": {"callFrames": []}
        },
        {
            "level": "warn",
            "timestamp": 1234567892,
            "args": ["Warning message"],
            "stackTrace": None
        }
    ]


@pytest.fixture
def sample_page_elements():
    """Sample interactive elements data"""
    return {
        "buttons": [
            {
                "text": "Submit",
                "tag": "BUTTON",
                "x": 100,
                "y": 200,
                "role": "button",
                "visible": True
            }
        ],
        "links": [
            {
                "text": "Home",
                "tag": "A",
                "href": "https://example.com",
                "x": 50,
                "y": 50,
                "visible": True
            }
        ],
        "inputs": [
            {
                "type": "text",
                "name": "username",
                "placeholder": "Enter username",
                "x": 150,
                "y": 250,
                "visible": True
            }
        ]
    }


@pytest.fixture
def sample_html():
    """Sample HTML content"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <h1>Test Heading</h1>
        <button id="submit-btn">Submit</button>
        <a href="/home">Home</a>
        <input type="text" name="username" placeholder="Enter username">
    </body>
    </html>
    """


@pytest.fixture
def mock_cdp_response():
    """Mock CDP method response"""
    def _mock_response(success=True, result=None, error=None):
        if success:
            return {"result": result or {"value": "success"}}
        else:
            return {"error": error or {"message": "CDP error"}}

    return _mock_response


# Async test helper
@pytest.fixture
def async_test():
    """Helper for running async tests"""
    import asyncio

    def _run_async(coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)

    return _run_async
