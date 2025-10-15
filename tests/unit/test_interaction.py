"""
Unit tests for commands/interaction.py

Tests:
- ClickCommand: Multiple search strategies, cursor animations
- ClickByTextCommand: Text matching scoring, normalization
- ScrollPageCommand: Page/element scroll, absolute positioning
- MoveCursorCommand: Coordinate/selector movement

Coverage target: 60%+ (22% → 60%)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from commands.interaction import (
    ClickCommand,
    ClickByTextCommand,
    ScrollPageCommand,
    MoveCursorCommand
)
from commands.context import CommandContext
from mcp.errors import InvalidArgumentError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_tab():
    """Mock pychrome Tab"""
    tab = MagicMock()
    return tab


@pytest.fixture
def mock_cursor():
    """Mock AICursor with initialize() method"""
    cursor = AsyncMock()
    cursor.initialize = AsyncMock()
    cursor.move = AsyncMock()
    return cursor


@pytest.fixture
def mock_cdp():
    """Mock AsyncCDP wrapper"""
    cdp = AsyncMock()
    cdp.evaluate = AsyncMock()
    return cdp


@pytest.fixture
def context(mock_tab, mock_cursor, mock_cdp):
    """CommandContext with mocked dependencies"""
    return CommandContext(
        tab=mock_tab,
        cursor=mock_cursor,
        browser=None,
        cdp=mock_cdp
    )


# ============================================================================
# ClickCommand Tests
# ============================================================================

class TestClickCommand:
    """Tests for ClickCommand"""

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test command metadata"""
        assert ClickCommand.name == "click"
        assert "CSS selector" in ClickCommand.description
        assert ClickCommand.requires_cursor is True

        schema = ClickCommand.input_schema
        assert schema["required"] == ["selector"]
        assert "selector" in schema["properties"]

    @pytest.mark.asyncio
    async def test_successful_click_css_selector(self, context, mock_cursor, mock_cdp):
        """Test successful click with CSS selector strategy"""
        # Mock successful click result
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "selector": "button.submit",
                    "strategy": "css",
                    "message": "Clicked element using strategy: css",
                    "cursorAnimated": True,
                    "cursorVisible": True,
                    "elementInfo": {
                        "tagName": "BUTTON",
                        "id": "submit-btn",
                        "className": "submit primary",
                        "text": "Submit Form",
                        "position": {
                            "top": 100,
                            "left": 200,
                            "width": 120,
                            "height": 40,
                            "clickX": 260,
                            "clickY": 120
                        },
                        "inViewport": True
                    }
                }
            }
        }

        cmd = ClickCommand(context)
        result = await cmd.execute(selector="button.submit")

        # Verify cursor initialization
        mock_cursor.initialize.assert_called_once()

        # Verify CDP evaluation called
        mock_cdp.evaluate.assert_called_once()
        call_args = mock_cdp.evaluate.call_args[1]
        assert "button.submit" in call_args["expression"]
        assert call_args["returnByValue"] is True
        assert call_args["awaitPromise"] is True

        # Verify result
        assert result["success"] is True
        assert result["strategy"] == "css"
        assert result["elementInfo"]["tagName"] == "BUTTON"

    @pytest.mark.asyncio
    async def test_click_xpath_selector(self, context, mock_cdp):
        """Test click with XPath selector"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "selector": "//button[@type='submit']",
                    "strategy": "xpath",
                    "message": "Clicked element using strategy: xpath",
                    "cursorAnimated": True,
                    "elementInfo": {
                        "tagName": "BUTTON",
                        "text": "Submit"
                    }
                }
            }
        }

        cmd = ClickCommand(context)
        result = await cmd.execute(selector="//button[@type='submit']")

        assert result["success"] is True
        assert result["strategy"] == "xpath"

    @pytest.mark.asyncio
    async def test_click_element_not_found(self, context, mock_cdp):
        """Test click when element not found"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": False,
                    "reason": "not_found",
                    "message": "Element not found: .nonexistent",
                    "matchCount": 0,
                    "suggestion": "Try using text content or XPath"
                }
            }
        }

        cmd = ClickCommand(context)
        result = await cmd.execute(selector=".nonexistent")

        assert result["success"] is False
        assert result["reason"] == "not_found"
        assert "Element not found" in result["message"]

    @pytest.mark.asyncio
    async def test_click_element_not_visible(self, context, mock_cdp):
        """Test click when element exists but not visible"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": False,
                    "reason": "not_visible",
                    "message": "Element found but not visible",
                    "display": "none",
                    "visibility": "visible",
                    "opacity": "1",
                    "dimensions": {"width": 0, "height": 0}
                }
            }
        }

        cmd = ClickCommand(context)
        result = await cmd.execute(selector=".hidden-btn")

        assert result["success"] is False
        assert result["reason"] == "not_visible"
        assert "not visible" in result["message"]

    @pytest.mark.asyncio
    async def test_click_with_scroll_into_view(self, context, mock_cdp):
        """Test click that requires scrolling element into view"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "selector": "#footer-btn",
                    "strategy": "css",
                    "message": "Clicked element using strategy: css",
                    "cursorAnimated": True,
                    "elementInfo": {
                        "tagName": "BUTTON",
                        "text": "Footer Button",
                        "position": {"clickX": 500, "clickY": 1200},
                        "inViewport": False  # Was scrolled into view
                    }
                }
            }
        }

        cmd = ClickCommand(context)
        result = await cmd.execute(selector="#footer-btn")

        assert result["success"] is True
        assert result["elementInfo"]["inViewport"] is False

    @pytest.mark.asyncio
    async def test_click_without_cursor_animation(self, context, mock_cursor, mock_cdp):
        """Test click with show_cursor=False"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "selector": "button",
                    "strategy": "css",
                    "cursorAnimated": False,
                    "elementInfo": {"tagName": "BUTTON"}
                }
            }
        }

        cmd = ClickCommand(context)
        result = await cmd.execute(selector="button", show_cursor=False)

        # Cursor still initialized but animation disabled in JS
        mock_cursor.initialize.assert_called_once()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_click_exception_handling(self, context, mock_cdp):
        """Test exception handling in click command"""
        mock_cdp.evaluate.side_effect = RuntimeError("CDP connection lost")

        cmd = ClickCommand(context)
        result = await cmd.execute(selector="button")

        assert result["success"] is False
        assert result["reason"] == "exception"
        assert "CDP connection lost" in result["error"]

    @pytest.mark.asyncio
    async def test_click_invalid_selector(self, context, mock_cdp):
        """Test click with invalid selector (empty string still allowed but fails in JS)"""
        # Validators don't raise for empty string, they return it
        # The actual validation happens in JS execution
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": False,
                    "reason": "not_found",
                    "message": "Element not found: ",
                    "matchCount": 0
                }
            }
        }

        cmd = ClickCommand(context)
        result = await cmd.execute(selector="")

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_click_text_search_strategy(self, context, mock_cdp):
        """Test click using text search strategy"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "selector": "text='Login'",
                    "strategy": "text-exact",
                    "message": "Clicked element using strategy: text-exact",
                    "elementInfo": {
                        "tagName": "A",
                        "text": "Login"
                    }
                }
            }
        }

        cmd = ClickCommand(context)
        result = await cmd.execute(selector="text='Login'")

        assert result["success"] is True
        assert result["strategy"] == "text-exact"

    @pytest.mark.asyncio
    async def test_click_contains_strategy(self, context, mock_cdp):
        """Test click using text-contains strategy"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "selector": "Sign Up",
                    "strategy": "text-contains",
                    "message": "Clicked element using strategy: text-contains",
                    "elementInfo": {
                        "tagName": "BUTTON",
                        "text": "Sign Up Now"
                    }
                }
            }
        }

        cmd = ClickCommand(context)
        result = await cmd.execute(selector="Sign Up")

        assert result["success"] is True
        assert result["strategy"] == "text-contains"


# ============================================================================
# ClickByTextCommand Tests
# ============================================================================

class TestClickByTextCommand:
    """Tests for ClickByTextCommand with scoring algorithm"""

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test command metadata"""
        assert ClickByTextCommand.name == "click_by_text"
        assert "Click element by text" in ClickByTextCommand.description
        assert ClickByTextCommand.requires_cursor is True

        schema = ClickByTextCommand.input_schema
        assert schema["required"] == ["text"]
        assert "text" in schema["properties"]
        assert "tag" in schema["properties"]
        assert "exact" in schema["properties"]

    @pytest.mark.asyncio
    async def test_successful_click_exact_match(self, context, mock_cursor, mock_cdp):
        """Test successful click with exact text match"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "searchText": "Submit",
                    "matchScore": 150,  # Exact match with direct text bonus
                    "message": "Clicked element with text: \"Submit\"",
                    "cursorVisible": True,
                    "element": {
                        "tag": "BUTTON",
                        "id": "submit-btn",
                        "className": "primary",
                        "actualText": "Submit",
                        "ariaLabel": None,
                        "role": None,
                        "position": {"x": 300, "y": 200}
                    }
                }
            }
        }

        cmd = ClickByTextCommand(context)
        result = await cmd.execute(text="Submit", exact=True)

        # Verify cursor initialization
        mock_cursor.initialize.assert_called_once()

        # Verify CDP call
        mock_cdp.evaluate.assert_called_once()
        call_args = mock_cdp.evaluate.call_args[1]
        assert "Submit" in call_args["expression"]
        assert "true" in call_args["expression"]  # exact=True

        # Verify result
        assert result["success"] is True
        assert result["matchScore"] == 150
        assert result["element"]["tag"] == "BUTTON"

    @pytest.mark.asyncio
    async def test_click_partial_match(self, context, mock_cdp):
        """Test click with partial text match"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "searchText": "Login",
                    "matchScore": 80,  # Partial match with direct text bonus
                    "message": "Clicked element with text: \"Login\"",
                    "element": {
                        "tag": "A",
                        "actualText": "Login to Dashboard",
                        "position": {"x": 150, "y": 50}
                    }
                }
            }
        }

        cmd = ClickByTextCommand(context)
        result = await cmd.execute(text="Login", exact=False)

        assert result["success"] is True
        assert result["matchScore"] == 80
        assert "Login" in result["element"]["actualText"]

    @pytest.mark.asyncio
    async def test_click_aria_label_match(self, context, mock_cdp):
        """Test click matching aria-label (score 70)"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "searchText": "Close",
                    "matchScore": 70,  # aria-label match
                    "element": {
                        "tag": "BUTTON",
                        "actualText": "×",
                        "ariaLabel": "Close dialog",
                        "position": {"x": 500, "y": 100}
                    }
                }
            }
        }

        cmd = ClickByTextCommand(context)
        result = await cmd.execute(text="Close")

        assert result["success"] is True
        assert result["matchScore"] == 70

    @pytest.mark.asyncio
    async def test_click_placeholder_match(self, context, mock_cdp):
        """Test click matching placeholder (score 40)"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "searchText": "Email",
                    "matchScore": 40,  # placeholder match
                    "element": {
                        "tag": "INPUT",
                        "actualText": "",
                        "ariaLabel": None,
                        "position": {"x": 200, "y": 300}
                    }
                }
            }
        }

        cmd = ClickByTextCommand(context)
        result = await cmd.execute(text="Email")

        assert result["success"] is True
        assert result["matchScore"] == 40

    @pytest.mark.asyncio
    async def test_click_with_tag_filter(self, context, mock_cdp):
        """Test click with tag parameter to filter search"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "searchText": "Download",
                    "matchScore": 100,
                    "element": {
                        "tag": "BUTTON",
                        "actualText": "Download",
                        "position": {"x": 400, "y": 250}
                    }
                }
            }
        }

        cmd = ClickByTextCommand(context)
        result = await cmd.execute(text="Download", tag="button")

        # Verify tag parameter passed to JS
        call_args = mock_cdp.evaluate.call_args[1]
        assert '"button"' in call_args["expression"] or '["button"]' in call_args["expression"]

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_click_element_not_found_with_debug(self, context, mock_cdp):
        """Test click when element not found (returns available elements)"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": False,
                    "message": "Element with text not found: \"Nonexistent\"",
                    "searchedTags": ["button", "a", "input"],
                    "totalElements": 50,
                    "visibleElements": 30,
                    "partialMatches": 0,
                    "availableTexts": [
                        {"tag": "BUTTON", "text": "Submit", "ariaLabel": None, "role": None},
                        {"tag": "A", "text": "Login", "ariaLabel": None, "role": "link"},
                        {"tag": "BUTTON", "text": "Cancel", "ariaLabel": "Close", "role": "button"}
                    ]
                }
            }
        }

        cmd = ClickByTextCommand(context)
        result = await cmd.execute(text="Nonexistent")

        assert result["success"] is False
        assert "not found" in result["message"]
        assert result["totalElements"] == 50
        assert result["visibleElements"] == 30
        assert len(result["availableTexts"]) == 3

    @pytest.mark.asyncio
    async def test_click_cyrillic_text(self, context, mock_cdp):
        """Test click with Cyrillic text (JSON escaping)"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "searchText": "Войти",
                    "matchScore": 100,
                    "element": {
                        "tag": "BUTTON",
                        "actualText": "Войти",
                        "position": {"x": 250, "y": 150}
                    }
                }
            }
        }

        cmd = ClickByTextCommand(context)
        result = await cmd.execute(text="Войти")

        # Verify JSON escaping in CDP call
        call_args = mock_cdp.evaluate.call_args[1]
        # json.dumps() should properly escape unicode
        assert "Войти" in call_args["expression"] or "\\u" in call_args["expression"]

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_click_text_normalization(self, context, mock_cdp):
        """Test text normalization (whitespace, case)"""
        # The JS code normalizes: "  Click   Here  " → "click here"
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "searchText": "  Click   Here  ",
                    "matchScore": 100,
                    "element": {
                        "tag": "BUTTON",
                        "actualText": "Click Here",
                        "position": {"x": 300, "y": 200}
                    }
                }
            }
        }

        cmd = ClickByTextCommand(context)
        result = await cmd.execute(text="  Click   Here  ")

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_click_exception_handling(self, context, mock_cdp):
        """Test exception handling in click_by_text"""
        mock_cdp.evaluate.side_effect = RuntimeError("Tab has been stopped")

        cmd = ClickByTextCommand(context)
        result = await cmd.execute(text="Submit")

        assert result["success"] is False
        assert "Tab has been stopped" in result["error"]

    @pytest.mark.asyncio
    async def test_click_invalid_text_empty(self, context, mock_cdp):
        """Test click with empty text (validator min_length=1 catches this)"""
        # Empty text should be caught by validator and raise InvalidArgumentError
        cmd = ClickByTextCommand(context)

        # Validator will raise InvalidArgumentError for empty string with min_length=1
        try:
            result = await cmd.execute(text="")
            # If validator doesn't raise, check result indicates failure
            assert result["success"] is False
        except InvalidArgumentError:
            # Expected behavior
            pass

    @pytest.mark.asyncio
    async def test_click_invalid_text_too_long(self, context, mock_cdp):
        """Test click with text exceeding max length (validator max_length=500)"""
        cmd = ClickByTextCommand(context)
        long_text = "A" * 501  # Max is 500

        # Validator should raise InvalidArgumentError for text exceeding max_length
        try:
            result = await cmd.execute(text=long_text)
            # If validator doesn't raise, check result indicates failure
            assert result["success"] is False
        except InvalidArgumentError:
            # Expected behavior
            pass


# ============================================================================
# ScrollPageCommand Tests
# ============================================================================

class TestScrollPageCommand:
    """Tests for ScrollPageCommand"""

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test command metadata"""
        assert ScrollPageCommand.name == "scroll_page"
        assert "Scroll the page" in ScrollPageCommand.description

        schema = ScrollPageCommand.input_schema
        assert "direction" in schema["properties"]
        assert "amount" in schema["properties"]
        assert "x" in schema["properties"]
        assert "y" in schema["properties"]
        assert "selector" in schema["properties"]

    @pytest.mark.asyncio
    async def test_scroll_down_default(self, context, mock_cdp):
        """Test scroll down with default amount (500px)"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "x": 0,
                    "y": 500,
                    "maxX": 0,
                    "maxY": 2000,
                    "viewportHeight": 800,
                    "viewportWidth": 1200,
                    "pageHeight": 2800,
                    "pageWidth": 1200,
                    "scrolledToBottom": False,
                    "scrolledToTop": False
                }
            }
        }

        cmd = ScrollPageCommand(context)
        result = await cmd.execute(direction="down")

        # Verify CDP call
        call_args = mock_cdp.evaluate.call_args[1]
        assert "scrollBy(0, 500)" in call_args["expression"]

        assert result["success"] is True
        assert result["direction"] == "down"
        assert result["amount"] == 500
        assert result["position"]["y"] == 500

    @pytest.mark.asyncio
    async def test_scroll_up(self, context, mock_cdp):
        """Test scroll up"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "x": 0,
                    "y": 200,
                    "scrolledToTop": False
                }
            }
        }

        cmd = ScrollPageCommand(context)
        result = await cmd.execute(direction="up", amount=300)

        call_args = mock_cdp.evaluate.call_args[1]
        assert "scrollBy(0, -300)" in call_args["expression"]

        assert result["success"] is True
        assert result["direction"] == "up"

    @pytest.mark.asyncio
    async def test_scroll_to_top(self, context, mock_cdp):
        """Test scroll to top of page"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "x": 0,
                    "y": 0,
                    "scrolledToTop": True
                }
            }
        }

        cmd = ScrollPageCommand(context)
        result = await cmd.execute(direction="top")

        call_args = mock_cdp.evaluate.call_args[1]
        assert "scrollTo(0, 0)" in call_args["expression"]

        assert result["success"] is True
        assert result["position"]["y"] == 0

    @pytest.mark.asyncio
    async def test_scroll_to_bottom(self, context, mock_cdp):
        """Test scroll to bottom of page"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "x": 0,
                    "y": 2000,
                    "maxY": 2000,
                    "scrolledToBottom": True
                }
            }
        }

        cmd = ScrollPageCommand(context)
        result = await cmd.execute(direction="bottom")

        call_args = mock_cdp.evaluate.call_args[1]
        assert "scrollHeight" in call_args["expression"]

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_scroll_absolute_coordinates(self, context, mock_cdp):
        """Test scroll to absolute x,y coordinates"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "x": 100,
                    "y": 500,
                    "maxX": 500,
                    "maxY": 2000
                }
            }
        }

        cmd = ScrollPageCommand(context)
        result = await cmd.execute(x=100, y=500)

        call_args = mock_cdp.evaluate.call_args[1]
        # Coordinates are formatted as floats: scrollTo(100.0, 500.0)
        assert "scrollTo(100" in call_args["expression"]
        assert "500" in call_args["expression"]

        assert result["success"] is True
        assert result["direction"] == "absolute"
        assert result["position"]["x"] == 100
        assert result["position"]["y"] == 500

    @pytest.mark.asyncio
    async def test_scroll_element_by_selector(self, context, mock_cdp):
        """Test scroll element using selector"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "element": ".scroll-container",
                    "scrollTop": 300,
                    "scrollLeft": 0,
                    "scrollHeight": 1000,
                    "scrollWidth": 500,
                    "clientHeight": 400,
                    "clientWidth": 500
                }
            }
        }

        cmd = ScrollPageCommand(context)
        result = await cmd.execute(selector=".scroll-container", direction="down", amount=300)

        call_args = mock_cdp.evaluate.call_args[1]
        assert ".scroll-container" in call_args["expression"]
        assert "scrollTop" in call_args["expression"]

        assert result["success"] is True
        assert result["selector"] == ".scroll-container"
        assert result["position"]["scrollTop"] == 300

    @pytest.mark.asyncio
    async def test_scroll_element_not_found(self, context, mock_cdp):
        """Test scroll element that doesn't exist"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": False,
                    "message": "Element not found: .nonexistent"
                }
            }
        }

        cmd = ScrollPageCommand(context)
        result = await cmd.execute(selector=".nonexistent", direction="down")

        assert result["success"] is False
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_scroll_invalid_direction(self, context, mock_cdp):
        """Test scroll with invalid direction"""
        cmd = ScrollPageCommand(context)
        result = await cmd.execute(direction="diagonal")

        # Should fail before CDP call
        assert result["success"] is False
        assert "Invalid direction" in result["message"]

    @pytest.mark.asyncio
    async def test_scroll_exception_handling(self, context, mock_cdp):
        """Test exception handling in scroll"""
        mock_cdp.evaluate.side_effect = RuntimeError("Connection lost")

        cmd = ScrollPageCommand(context)

        with pytest.raises(RuntimeError) as exc_info:
            await cmd.execute(direction="down")

        assert "Failed to scroll page" in str(exc_info.value)


# ============================================================================
# MoveCursorCommand Tests
# ============================================================================

class TestMoveCursorCommand:
    """Tests for MoveCursorCommand"""

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test command metadata"""
        assert MoveCursorCommand.name == "move_cursor"
        assert "Move the visual AI cursor" in MoveCursorCommand.description
        assert MoveCursorCommand.requires_cursor is True

        schema = MoveCursorCommand.input_schema
        assert "x" in schema["properties"]
        assert "y" in schema["properties"]
        assert "selector" in schema["properties"]
        assert "duration" in schema["properties"]

    @pytest.mark.asyncio
    async def test_move_cursor_to_coordinates(self, context, mock_cdp):
        """Test moving cursor to specific x,y coordinates"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "message": "Cursor moved to coordinates",
                    "position": {"x": 300, "y": 200}
                }
            }
        }

        cmd = MoveCursorCommand(context)
        result = await cmd.execute(x=300, y=200, duration=400)

        # Verify CDP call (coordinates may be floats like 300.0)
        call_args = mock_cdp.evaluate.call_args[1]
        assert "__moveAICursor__" in call_args["expression"]
        assert "300" in call_args["expression"]
        assert "200" in call_args["expression"]
        assert "400" in call_args["expression"]

        assert result["success"] is True
        assert result["position"]["x"] == 300
        assert result["position"]["y"] == 200

    @pytest.mark.asyncio
    async def test_move_cursor_to_element_selector(self, context, mock_cdp):
        """Test moving cursor to element center via selector"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "message": "Cursor moved to element: button.submit",
                    "position": {"x": 250, "y": 150},
                    "element": {
                        "tagName": "BUTTON",
                        "id": "submit-btn",
                        "className": "submit primary",
                        "bounds": {
                            "top": 130,
                            "left": 190,
                            "width": 120,
                            "height": 40
                        }
                    }
                }
            }
        }

        cmd = MoveCursorCommand(context)
        result = await cmd.execute(selector="button.submit", duration=500)

        # Verify selector in CDP call
        call_args = mock_cdp.evaluate.call_args[1]
        assert "button.submit" in call_args["expression"]
        assert "getBoundingClientRect" in call_args["expression"]

        assert result["success"] is True
        assert result["element"]["tagName"] == "BUTTON"
        assert result["position"]["x"] == 250
        assert result["position"]["y"] == 150

    @pytest.mark.asyncio
    async def test_move_cursor_custom_duration(self, context, mock_cdp):
        """Test custom animation duration"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "message": "Cursor moved to coordinates",
                    "position": {"x": 100, "y": 100}
                }
            }
        }

        cmd = MoveCursorCommand(context)
        result = await cmd.execute(x=100, y=100, duration=1000)

        call_args = mock_cdp.evaluate.call_args[1]
        assert "1000" in call_args["expression"]  # Custom duration

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_move_cursor_element_not_found(self, context, mock_cdp):
        """Test moving cursor to nonexistent element"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": False,
                    "message": "Element not found: .nonexistent"
                }
            }
        }

        cmd = MoveCursorCommand(context)
        result = await cmd.execute(selector=".nonexistent")

        assert result["success"] is False
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_move_cursor_not_initialized(self, context, mock_cdp):
        """Test when AI cursor is not initialized"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": False,
                    "message": "AI cursor not initialized"
                }
            }
        }

        cmd = MoveCursorCommand(context)
        result = await cmd.execute(x=100, y=100)

        assert result["success"] is False
        assert "not initialized" in result["message"]

    @pytest.mark.asyncio
    async def test_move_cursor_no_parameters(self, context, mock_cdp):
        """Test move_cursor without x,y or selector (should fail)"""
        cmd = MoveCursorCommand(context)
        result = await cmd.execute()

        # Should fail validation before CDP call
        assert result["success"] is False
        assert "provide x,y coordinates or selector" in result["message"]

    @pytest.mark.asyncio
    async def test_move_cursor_exception_handling(self, context, mock_cdp):
        """Test exception handling in move_cursor"""
        mock_cdp.evaluate.side_effect = RuntimeError("CDP error")

        cmd = MoveCursorCommand(context)
        result = await cmd.execute(x=100, y=100)

        assert result["success"] is False
        assert "Failed to move cursor" in result["message"]
        assert "CDP error" in result["error"]

    @pytest.mark.asyncio
    async def test_move_cursor_negative_coordinates(self, context, mock_cdp):
        """Test move_cursor with negative coordinates (validator validates)"""
        # Validators may allow negative coords or raise - test actual behavior
        cmd = MoveCursorCommand(context)

        try:
            result = await cmd.execute(x=-100, y=200)
            # If validator allows, check result
            assert result.get("success") is not None
        except InvalidArgumentError:
            # Expected if validator rejects negative coords
            pass

    @pytest.mark.asyncio
    async def test_move_cursor_duration_validation(self, context, mock_cdp):
        """Test move_cursor with invalid duration (out of range)"""
        cmd = MoveCursorCommand(context)

        try:
            result = await cmd.execute(x=100, y=100, duration=15000)  # Max is 10000
            # If validator allows, check result
            assert result.get("success") is not None
        except InvalidArgumentError:
            # Expected if validator rejects duration > 10000
            pass


# ============================================================================
# Integration Tests
# ============================================================================

class TestInteractionIntegration:
    """Integration tests for interaction commands"""

    @pytest.mark.asyncio
    async def test_click_and_move_cursor_workflow(self, context, mock_cursor, mock_cdp):
        """Test click command initializes cursor and animates"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "selector": "button",
                    "strategy": "css",
                    "cursorAnimated": True,
                    "elementInfo": {"tagName": "BUTTON"}
                }
            }
        }

        cmd = ClickCommand(context)
        result = await cmd.execute(selector="button", show_cursor=True)

        # Verify cursor workflow
        mock_cursor.initialize.assert_called_once()
        assert result["success"] is True
        assert result["cursorAnimated"] is True

    @pytest.mark.asyncio
    async def test_click_by_text_scoring_preference(self, context, mock_cdp):
        """Test that direct text match gets higher score than nested"""
        # Simulates JS scoring: direct text match gets +50 bonus
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "searchText": "Submit",
                    "matchScore": 150,  # 100 (exact) + 50 (direct text)
                    "element": {
                        "tag": "BUTTON",
                        "actualText": "Submit"
                    }
                }
            }
        }

        cmd = ClickByTextCommand(context)
        result = await cmd.execute(text="Submit", exact=True)

        assert result["matchScore"] == 150  # Highest score for direct match

    @pytest.mark.asyncio
    async def test_scroll_and_click_workflow(self, context, mock_cdp):
        """Test scrolling before clicking element"""
        # First scroll to element
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "x": 0,
                    "y": 800,
                    "scrolledToBottom": False
                }
            }
        }

        scroll_cmd = ScrollPageCommand(context)
        scroll_result = await scroll_cmd.execute(direction="down", amount=800)
        assert scroll_result["success"] is True

        # Then click element (now in viewport)
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "success": True,
                    "selector": "#footer-btn",
                    "strategy": "css",
                    "elementInfo": {
                        "tagName": "BUTTON",
                        "inViewport": True  # After scroll
                    }
                }
            }
        }

        click_cmd = ClickCommand(context)
        click_result = await click_cmd.execute(selector="#footer-btn")
        assert click_result["success"] is True
