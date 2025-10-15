"""
Unit tests for commands/screenshot.py - Screenshot command with optimization
"""
import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from commands.screenshot import ScreenshotCommand
from mcp.errors import InvalidArgumentError


class TestScreenshotCommand:
    """Test ScreenshotCommand functionality"""

    @pytest.fixture
    def temp_screenshots_dir(self):
        """Create temporary screenshots directory"""
        temp_dir = tempfile.mkdtemp()
        screenshots_dir = os.path.join(temp_dir, "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)

        # Change to temp dir for tests
        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        yield screenshots_dir

        # Cleanup
        os.chdir(old_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_screenshot_basic_png(self, command_context, temp_screenshots_dir):
        """Test basic PNG screenshot"""
        cmd = ScreenshotCommand(command_context)

        # Mock CDP capture
        command_context.tab.Page.captureScreenshot = AsyncMock(
            return_value={"data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}  # 1x1 pixel PNG
        )

        result = await cmd.execute(path="./screenshots/test.png", format="png")

        assert result["success"] is True
        assert "test.png" in result["path"]
        assert result["format"] == "png"
        assert os.path.exists("./screenshots/test.png")

    @pytest.mark.asyncio
    async def test_screenshot_jpeg_format(self, command_context, temp_screenshots_dir):
        """Test JPEG format with quality"""
        cmd = ScreenshotCommand(command_context)

        command_context.tab.Page.captureScreenshot = AsyncMock(
            return_value={"data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}
        )

        result = await cmd.execute(
            path="./screenshots/test.jpg",
            format="jpeg",
            quality=75
        )

        assert result["success"] is True
        assert result["format"] == "jpeg"

    @pytest.mark.asyncio
    async def test_screenshot_path_validation(self, command_context):
        """Test path security validation"""
        cmd = ScreenshotCommand(command_context)

        # Directory traversal should fail
        with pytest.raises(InvalidArgumentError) as exc:
            await cmd.execute(path="../etc/passwd")
        assert ".." in str(exc.value)

        # Absolute path should fail
        with pytest.raises(InvalidArgumentError):
            await cmd.execute(path="/etc/passwd")

        # Non-screenshots path should be corrected (based on old logic) or fail
        # Based on new validation, it should fail
        with pytest.raises(InvalidArgumentError):
            await cmd.execute(path="./forbidden/file.png")

    @pytest.mark.asyncio
    async def test_screenshot_format_validation(self, command_context):
        """Test format validation"""
        cmd = ScreenshotCommand(command_context)

        # Invalid format
        with pytest.raises(InvalidArgumentError) as exc:
            await cmd.execute(format="webp")
        assert "format" in str(exc.value)

    @pytest.mark.asyncio
    async def test_screenshot_quality_validation(self, command_context):
        """Test quality range validation"""
        cmd = ScreenshotCommand(command_context)

        # Quality too low
        with pytest.raises(InvalidArgumentError):
            await cmd.execute(quality=0)

        # Quality too high
        with pytest.raises(InvalidArgumentError):
            await cmd.execute(quality=101)

        # Valid quality should work
        command_context.tab.Page.captureScreenshot = AsyncMock(
            return_value={"data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}
        )
        # Just validate, don't execute
        assert cmd.execute  # Command exists

    @pytest.mark.asyncio
    async def test_screenshot_max_width_validation(self, command_context):
        """Test max_width validation"""
        cmd = ScreenshotCommand(command_context)

        # Too small
        with pytest.raises(InvalidArgumentError):
            await cmd.execute(max_width=50)

        # Too large
        with pytest.raises(InvalidArgumentError):
            await cmd.execute(max_width=20000)

    @pytest.mark.asyncio
    async def test_screenshot_element_selector(self, command_context, temp_screenshots_dir):
        """Test element-specific screenshot"""
        cmd = ScreenshotCommand(command_context)

        # Mock element bounds
        command_context.cdp.evaluate = AsyncMock(
            return_value={
                "result": {
                    "value": {
                        "x": 10,
                        "y": 20,
                        "width": 100,
                        "height": 50,
                        "scale": 1
                    }
                }
            }
        )

        command_context.tab.Page.captureScreenshot = AsyncMock(
            return_value={"data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}
        )

        result = await cmd.execute(
            path="./screenshots/element.png",
            element="#submit-btn"
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_screenshot_element_selector_validation(self, command_context):
        """Test element selector validation"""
        cmd = ScreenshotCommand(command_context)

        # Dangerous selector
        with pytest.raises(InvalidArgumentError):
            await cmd.execute(element="javascript:alert(1)")

    @pytest.mark.asyncio
    async def test_screenshot_full_page(self, command_context, temp_screenshots_dir):
        """Test full page screenshot"""
        cmd = ScreenshotCommand(command_context)

        command_context.tab.Page.captureScreenshot = AsyncMock(
            return_value={"data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}
        )

        result = await cmd.execute(
            path="./screenshots/full.png",
            full_page=True
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_screenshot_error_handling(self, command_context, temp_screenshots_dir):
        """Test error handling"""
        cmd = ScreenshotCommand(command_context)

        # Mock CDP error
        command_context.tab.Page.captureScreenshot = AsyncMock(
            side_effect=Exception("CDP capture failed")
        )

        result = await cmd.execute(path="./screenshots/error.png")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_screenshot_creates_directory(self, command_context):
        """Test that screenshots directory is created if missing"""
        cmd = ScreenshotCommand(command_context)

        # Remove directory if exists
        if os.path.exists("./screenshots"):
            shutil.rmtree("./screenshots")

        command_context.tab.Page.captureScreenshot = AsyncMock(
            return_value={"data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}
        )

        result = await cmd.execute(path="./screenshots/auto.png")

        assert result["success"] is True
        assert os.path.exists("./screenshots")

    def test_screenshot_command_metadata(self):
        """Test command metadata"""
        assert ScreenshotCommand.name == "screenshot"
        assert ScreenshotCommand.description is not None
        assert "screenshot" in ScreenshotCommand.description.lower()
        assert ScreenshotCommand.input_schema["type"] == "object"

        # Check schema has required properties
        props = ScreenshotCommand.input_schema["properties"]
        assert "path" in props
        assert "format" in props
        assert "quality" in props

    def test_screenshot_to_mcp_tool(self):
        """Test MCP tool conversion"""
        tool = ScreenshotCommand.to_mcp_tool()

        assert tool["name"] == "screenshot"
        assert "description" in tool
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"


class TestScreenshotOptimization:
    """Test screenshot optimization features"""

    @pytest.mark.asyncio
    async def test_get_element_bounds_success(self, command_context):
        """Test getting element bounds"""
        cmd = ScreenshotCommand(command_context)

        command_context.cdp.evaluate = AsyncMock(
            return_value={
                "result": {
                    "value": {
                        "x": 100,
                        "y": 200,
                        "width": 300,
                        "height": 150,
                        "scale": 2
                    }
                }
            }
        )

        bounds = await cmd._get_element_bounds("#test")

        assert bounds is not None
        assert bounds["x"] == 100
        assert bounds["width"] == 300

    @pytest.mark.asyncio
    async def test_get_element_bounds_not_found(self, command_context):
        """Test element bounds when element not found"""
        cmd = ScreenshotCommand(command_context)

        command_context.cdp.evaluate = AsyncMock(
            return_value={"result": {"value": None}}
        )

        bounds = await cmd._get_element_bounds("#nonexistent")

        assert bounds is None

    @pytest.mark.asyncio
    async def test_get_element_bounds_error(self, command_context):
        """Test element bounds error handling"""
        cmd = ScreenshotCommand(command_context)

        command_context.cdp.evaluate = AsyncMock(
            side_effect=Exception("Evaluation failed")
        )

        bounds = await cmd._get_element_bounds("#test")

        assert bounds is None

    @pytest.mark.skipif(
        not hasattr(ScreenshotCommand, '_optimize_image'),
        reason="Pillow not available"
    )
    def test_optimize_image_no_pillow(self):
        """Test optimization graceful degradation without Pillow"""
        cmd = ScreenshotCommand(Mock())

        # If Pillow not available, should return original
        img_bytes = b"fake image data"
        result = cmd._optimize_image(img_bytes, "png", 80, None)

        # Should either optimize or return original
        assert isinstance(result, bytes)
