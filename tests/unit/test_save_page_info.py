"""Unit tests for commands/save_page_info.py - Save page info command

Coverage target: 70%+
Focus: Execute, error handling, optimization, file I/O
"""
import pytest
import json
import os
from unittest.mock import AsyncMock, Mock, MagicMock, patch, mock_open
from commands.save_page_info import SavePageInfoCommand
from commands.context import CommandContext


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_cdp():
    """Create mock AsyncCDP wrapper"""
    cdp = AsyncMock()
    return cdp


@pytest.fixture
def mock_context(mock_cdp):
    """Create CommandContext with mocked CDP"""
    context = CommandContext(
        tab=Mock(),
        cursor=None,
        browser=None,
        cdp=mock_cdp
    )
    return context


@pytest.fixture
def sample_page_data():
    """Sample page data returned from JavaScript evaluation"""
    return {
        "url": "https://example.com",
        "title": "Example Page",
        "viewport": {
            "width": 1920,
            "height": 1080
        },
        "interactive_elements": [
            {
                "tag": "button",
                "text": "Click me",
                "id": "btn-1",
                "classes": ["btn", "btn-primary"],
                "position": {"x": 100, "y": 200}
            },
            {
                "tag": "a",
                "text": "Link",
                "id": None,
                "classes": [],
                "position": {"x": 300, "y": 400}
            }
        ],
        "console": {
            "logs": [
                {"level": "log", "message": "Test log"}
            ],
            "total": 1
        },
        "network": {
            "total_requests": 10,
            "failed": 0,
            "recent": [
                {"name": "script.js", "type": "script", "duration": 50}
            ]
        },
        "summary": {
            "total_buttons": 5,
            "total_links": 10,
            "visible_interactive": 2,
            "page_loaded": True
        }
    }


# ============================================================================
# SavePageInfoCommand Tests
# ============================================================================

class TestSavePageInfoCommand:
    """Test SavePageInfoCommand"""

    @pytest.mark.asyncio
    async def test_execute_default_params(self, mock_context, mock_cdp, sample_page_data):
        """Should save page info with default parameters"""
        # Setup mock
        mock_cdp.evaluate.return_value = {
            "result": {"value": sample_page_data}
        }

        with patch("builtins.open", mock_open()) as mock_file, \
             patch("os.makedirs") as mock_makedirs, \
             patch("os.path.getsize", return_value=3000):  # 3KB

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute()

            # Verify success
            assert result["success"] is True
            assert result["file"] == "./page_info.json"
            assert result["size_kb"] == 2.9  # 3000/1024 rounded
            assert result["optimized"] is True
            assert "page_info.json" in result["message"]
            assert "optimized mode" in result["message"]

            # Verify summary included
            assert "summary" in result
            assert result["summary"]["total_buttons"] == 5

            # Verify file operations
            mock_makedirs.assert_called_once_with(".", exist_ok=True)
            mock_file.assert_called_once_with("./page_info.json", "w", encoding="utf-8")

    @pytest.mark.asyncio
    async def test_execute_custom_output_file(self, mock_context, mock_cdp, sample_page_data):
        """Should save to custom file path"""
        mock_cdp.evaluate.return_value = {
            "result": {"value": sample_page_data}
        }

        with patch("builtins.open", mock_open()) as mock_file, \
             patch("os.makedirs") as mock_makedirs, \
             patch("os.path.getsize", return_value=2048):

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute(output_file="./custom/path.json")

            assert result["success"] is True
            assert result["file"] == "./custom/path.json"
            assert result["size_kb"] == 2.0

            # Verify directory creation
            mock_makedirs.assert_called_once_with("./custom", exist_ok=True)
            mock_file.assert_called_once_with("./custom/path.json", "w", encoding="utf-8")

    @pytest.mark.asyncio
    async def test_execute_full_mode(self, mock_context, mock_cdp, sample_page_data):
        """Should skip optimization when full=True"""
        mock_cdp.evaluate.return_value = {
            "result": {"value": sample_page_data}
        }

        with patch("builtins.open", mock_open()) as mock_file, \
             patch("os.makedirs"), \
             patch("os.path.getsize", return_value=10240):

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute(full=True)

            assert result["success"] is True
            assert result["optimized"] is False
            assert "full mode" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_optimized_mode(self, mock_context, mock_cdp, sample_page_data):
        """Should optimize data when full=False (default)"""
        mock_cdp.evaluate.return_value = {
            "result": {"value": sample_page_data}
        }

        written_data = None

        def capture_write(file, mode, encoding):
            m = mock_open()()
            original_write = m.write

            def write_wrapper(data):
                nonlocal written_data
                written_data = data
                return original_write(data)

            m.write = write_wrapper
            return m

        with patch("builtins.open", side_effect=capture_write), \
             patch("os.makedirs"), \
             patch("os.path.getsize", return_value=3000):

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute(full=False)

            assert result["success"] is True
            assert result["optimized"] is True

            # Verify optimization was called (data should be modified)
            # JsonOptimizer.optimize_page_info should have been invoked

    @pytest.mark.asyncio
    async def test_execute_creates_directory(self, mock_context, mock_cdp, sample_page_data):
        """Should create directory if it doesn't exist"""
        mock_cdp.evaluate.return_value = {
            "result": {"value": sample_page_data}
        }

        with patch("builtins.open", mock_open()), \
             patch("os.makedirs") as mock_makedirs, \
             patch("os.path.getsize", return_value=1024):

            cmd = SavePageInfoCommand(mock_context)
            await cmd.execute(output_file="./deep/nested/path/file.json")

            mock_makedirs.assert_called_once_with("./deep/nested/path", exist_ok=True)

    @pytest.mark.asyncio
    async def test_execute_root_directory(self, mock_context, mock_cdp, sample_page_data):
        """Should handle root directory (no dirname)"""
        mock_cdp.evaluate.return_value = {
            "result": {"value": sample_page_data}
        }

        with patch("builtins.open", mock_open()), \
             patch("os.makedirs") as mock_makedirs, \
             patch("os.path.getsize", return_value=1024):

            cmd = SavePageInfoCommand(mock_context)
            await cmd.execute(output_file="page.json")

            mock_makedirs.assert_called_once_with(".", exist_ok=True)

    @pytest.mark.asyncio
    async def test_execute_json_encoding(self, mock_context, mock_cdp):
        """Should handle UTF-8 encoding for non-ASCII characters"""
        unicode_data = {
            "url": "https://example.ru",
            "title": "Пример страницы",
            "interactive_elements": [
                {"tag": "button", "text": "Нажми меня", "id": None, "classes": [], "position": {"x": 100, "y": 200}}
            ],
            "console": {"logs": [], "total": 0},
            "network": {"total_requests": 0, "failed": 0, "recent": []},
            "summary": {"total_buttons": 1, "total_links": 0, "visible_interactive": 1, "page_loaded": True},
            "viewport": {"width": 1920, "height": 1080}
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": unicode_data}
        }

        written_content = None

        def capture_json(file, mode, encoding):
            assert encoding == "utf-8"
            m = mock_open()()
            original_write = m.write

            def write_wrapper(data):
                nonlocal written_content
                written_content = data
                return original_write(data)

            m.write = write_wrapper
            return m

        with patch("builtins.open", side_effect=capture_json), \
             patch("os.makedirs"), \
             patch("os.path.getsize", return_value=2048):

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_calculates_size_kb(self, mock_context, mock_cdp, sample_page_data):
        """Should calculate file size in KB correctly"""
        mock_cdp.evaluate.return_value = {
            "result": {"value": sample_page_data}
        }

        test_cases = [
            (1024, 1.0),    # 1KB
            (2048, 2.0),    # 2KB
            (3500, 3.4),    # 3.4KB
            (512, 0.5),     # 0.5KB
            (10240, 10.0)   # 10KB
        ]

        for file_size, expected_kb in test_cases:
            with patch("builtins.open", mock_open()), \
                 patch("os.makedirs"), \
                 patch("os.path.getsize", return_value=file_size):

                cmd = SavePageInfoCommand(mock_context)
                result = await cmd.execute()

                assert result["size_kb"] == expected_kb, f"Failed for {file_size} bytes"

    @pytest.mark.asyncio
    async def test_execute_empty_page_data(self, mock_context, mock_cdp):
        """Should handle empty page data gracefully"""
        mock_cdp.evaluate.return_value = {
            "result": {"value": {}}
        }

        with patch("builtins.open", mock_open()), \
             patch("os.makedirs"), \
             patch("os.path.getsize", return_value=100):

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is True
            assert result["summary"] == {}

    @pytest.mark.asyncio
    async def test_execute_missing_result_value(self, mock_context, mock_cdp):
        """Should handle missing 'value' in CDP response"""
        mock_cdp.evaluate.return_value = {
            "result": {}  # No 'value' key
        }

        with patch("builtins.open", mock_open()), \
             patch("os.makedirs"), \
             patch("os.path.getsize", return_value=100):

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_missing_result(self, mock_context, mock_cdp):
        """Should handle missing 'result' in CDP response"""
        mock_cdp.evaluate.return_value = {}

        with patch("builtins.open", mock_open()), \
             patch("os.makedirs"), \
             patch("os.path.getsize", return_value=100):

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is True


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestSavePageInfoErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_cdp_evaluate_fails(self, mock_context, mock_cdp):
        """Should handle CDP evaluation failure"""
        mock_cdp.evaluate.side_effect = Exception("CDP timeout")

        cmd = SavePageInfoCommand(mock_context)
        result = await cmd.execute()

        assert result["success"] is False
        assert "Failed to save page info" in result["message"]
        assert "CDP timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_file_write_permission_error(self, mock_context, mock_cdp, sample_page_data):
        """Should handle file write permission errors"""
        mock_cdp.evaluate.return_value = {
            "result": {"value": sample_page_data}
        }

        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is False
            assert "Failed to save page info" in result["message"]
            assert "Access denied" in result["error"]

    @pytest.mark.asyncio
    async def test_directory_creation_fails(self, mock_context, mock_cdp, sample_page_data):
        """Should handle directory creation failure"""
        mock_cdp.evaluate.return_value = {
            "result": {"value": sample_page_data}
        }

        with patch("os.makedirs", side_effect=OSError("Cannot create directory")):
            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is False
            assert "Cannot create directory" in result["error"]

    @pytest.mark.asyncio
    async def test_json_serialization_error(self, mock_context, mock_cdp):
        """Should handle JSON serialization errors"""
        # Create non-serializable data
        class NonSerializable:
            pass

        bad_data = {
            "url": "https://example.com",
            "title": "Test",
            "bad_object": NonSerializable(),  # Cannot be JSON serialized
            "interactive_elements": [],
            "console": {"logs": [], "total": 0},
            "network": {"total_requests": 0, "failed": 0},
            "summary": {},
            "viewport": {"width": 1920, "height": 1080}
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": bad_data}
        }

        # Mock json.dump to fail
        with patch("builtins.open", mock_open()), \
             patch("os.makedirs"), \
             patch("json.dump", side_effect=TypeError("Object of type NonSerializable is not JSON serializable")):

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is False
            assert "Failed to save page info" in result["message"]

    @pytest.mark.asyncio
    async def test_getsize_fails(self, mock_context, mock_cdp, sample_page_data):
        """Should handle os.path.getsize failure"""
        mock_cdp.evaluate.return_value = {
            "result": {"value": sample_page_data}
        }

        with patch("builtins.open", mock_open()), \
             patch("os.makedirs"), \
             patch("os.path.getsize", side_effect=OSError("File not found")):

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is False
            assert "File not found" in result["error"]

    @pytest.mark.asyncio
    async def test_optimizer_exception(self, mock_context, mock_cdp, sample_page_data):
        """Should handle JsonOptimizer exception"""
        mock_cdp.evaluate.return_value = {
            "result": {"value": sample_page_data}
        }

        with patch("commands.save_page_info.JsonOptimizer.optimize_page_info",
                   side_effect=Exception("Optimizer failed")):

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is False
            assert "Optimizer failed" in result["error"]


# ============================================================================
# Optimization Integration Tests
# ============================================================================

class TestSavePageInfoOptimization:
    """Test optimization logic integration"""

    @pytest.mark.asyncio
    async def test_optimization_reduces_elements(self, mock_context, mock_cdp):
        """Should reduce number of elements when optimizing"""
        # Create data with many elements
        many_elements = [
            {
                "tag": "button",
                "text": f"Button {i}",
                "id": f"btn-{i}",
                "classes": ["btn"],
                "position": {"x": 100, "y": i * 50}
            }
            for i in range(50)  # 50 elements
        ]

        large_data = {
            "url": "https://example.com",
            "title": "Test",
            "interactive_elements": many_elements,
            "console": {"logs": [], "total": 0},
            "network": {"total_requests": 0, "failed": 0, "recent": []},
            "summary": {"total_buttons": 50, "total_links": 0, "visible_interactive": 50, "page_loaded": True},
            "viewport": {"width": 1920, "height": 1080}
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": large_data}
        }

        saved_data = None

        def capture_json_dump(data, file, **kwargs):
            nonlocal saved_data
            saved_data = data

        with patch("builtins.open", mock_open()), \
             patch("os.makedirs"), \
             patch("os.path.getsize", return_value=2048), \
             patch("json.dump", side_effect=capture_json_dump):

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute(full=False)

            assert result["success"] is True

            # Verify optimization occurred
            assert saved_data is not None
            # Should have max 15 elements (as per JsonOptimizer)
            assert len(saved_data.get("interactive_elements", [])) <= 15

    @pytest.mark.asyncio
    async def test_full_mode_preserves_all_elements(self, mock_context, mock_cdp):
        """Should preserve all elements in full mode"""
        many_elements = [
            {
                "tag": "button",
                "text": f"Button {i}",
                "id": f"btn-{i}",
                "classes": ["btn"],
                "position": {"x": 100, "y": i * 50}
            }
            for i in range(50)
        ]

        large_data = {
            "url": "https://example.com",
            "title": "Test",
            "interactive_elements": many_elements,
            "console": {"logs": [], "total": 0},
            "network": {"total_requests": 0, "failed": 0, "recent": []},
            "summary": {"total_buttons": 50, "total_links": 0, "visible_interactive": 50, "page_loaded": True},
            "viewport": {"width": 1920, "height": 1080}
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": large_data}
        }

        saved_data = None

        def capture_json_dump(data, file, **kwargs):
            nonlocal saved_data
            saved_data = data

        with patch("builtins.open", mock_open()), \
             patch("os.makedirs"), \
             patch("os.path.getsize", return_value=10240), \
             patch("json.dump", side_effect=capture_json_dump):

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute(full=True)

            assert result["success"] is True

            # Should preserve all 50 elements
            assert len(saved_data.get("interactive_elements", [])) == 50

    @pytest.mark.asyncio
    async def test_optimization_handles_none_data(self, mock_context, mock_cdp):
        """Should handle None data in optimization"""
        mock_cdp.evaluate.return_value = {
            "result": {"value": None}
        }

        with patch("builtins.open", mock_open()), \
             patch("os.makedirs"), \
             patch("os.path.getsize", return_value=100):

            cmd = SavePageInfoCommand(mock_context)
            result = await cmd.execute(full=False)

            # Should not crash
            assert result["success"] is True


# ============================================================================
# Command Metadata Tests
# ============================================================================

class TestSavePageInfoMetadata:
    """Test command metadata (name, description, schema)"""

    def test_command_name(self):
        """Should have correct command name"""
        assert SavePageInfoCommand.name == "save_page_info"

    def test_command_description(self):
        """Should have descriptive description"""
        assert "Save complete page state" in SavePageInfoCommand.description
        assert "Read tool" in SavePageInfoCommand.description
        assert "page_info.json" in SavePageInfoCommand.description

    def test_input_schema_structure(self):
        """Should have valid input schema"""
        schema = SavePageInfoCommand.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_input_schema_output_file(self):
        """Should have output_file parameter in schema"""
        props = SavePageInfoCommand.input_schema["properties"]
        assert "output_file" in props
        assert props["output_file"]["type"] == "string"
        assert props["output_file"]["default"] == "./page_info.json"

    def test_input_schema_full_parameter(self):
        """Should have full parameter in schema"""
        props = SavePageInfoCommand.input_schema["properties"]
        assert "full" in props
        assert props["full"]["type"] == "boolean"
        assert props["full"]["default"] is False

    def test_no_required_parameters(self):
        """Should have no required parameters (all have defaults)"""
        schema = SavePageInfoCommand.input_schema
        # Either no 'required' key or empty list
        required = schema.get("required", [])
        assert len(required) == 0

    def test_requires_browser_false(self):
        """Should not require browser (only uses CDP)"""
        assert SavePageInfoCommand.requires_browser is False

    def test_requires_cursor_false(self):
        """Should not require cursor"""
        assert SavePageInfoCommand.requires_cursor is False

    def test_to_mcp_tool(self):
        """Should convert to MCP tool format correctly"""
        tool = SavePageInfoCommand.to_mcp_tool()
        assert tool["name"] == "save_page_info"
        assert "description" in tool
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"
