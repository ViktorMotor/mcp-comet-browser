"""
Unit tests for commands/base.py - Base Command class
"""
import pytest
from commands.base import Command
from commands.context import CommandContext
from typing import Dict, Any


class TestBaseCommand:
    """Test Command base class"""

    def test_command_is_abstract(self):
        """Command base class should be abstract"""
        with pytest.raises(TypeError):
            # Cannot instantiate abstract class
            Command(None)

    def test_command_metadata_attributes(self):
        """Command should have metadata as class attributes"""
        class TestCommand(Command):
            name = "test"
            description = "Test command"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return {"success": True}

        # Should have class attributes
        assert TestCommand.name == "test"
        assert TestCommand.description == "Test command"
        assert isinstance(TestCommand.input_schema, dict)

    def test_command_requires_execute(self):
        """Command subclass must implement execute()"""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            class BadCommand(Command):
                name = "bad"
                description = "No execute method"
                input_schema = {}
                # Missing execute() method

            BadCommand(None)

    def test_command_initialization(self, command_context):
        """Command should initialize with CommandContext"""
        class TestCommand(Command):
            name = "test"
            description = "Test"
            input_schema = {}

            async def execute(self, **kwargs):
                return {"success": True}

        cmd = TestCommand(command_context)

        assert cmd.context == command_context
        assert cmd.tab == command_context.tab

    def test_command_dependency_injection(self, command_context):
        """Command should receive dependencies from context"""
        class TestCommand(Command):
            name = "test"
            description = "Test"
            input_schema = {}
            requires_cursor = True
            requires_browser = True

            async def execute(self, **kwargs):
                return {"success": True}

        cmd = TestCommand(command_context)

        # Should receive cursor and browser from context
        assert cmd.cursor == command_context.cursor
        assert cmd.browser == command_context.browser
        assert cmd.cdp == command_context.cdp

    def test_command_without_dependencies(self, command_context):
        """Command without dependencies should work"""
        class SimpleCommand(Command):
            name = "simple"
            description = "Simple"
            input_schema = {}
            # No requires_* flags

            async def execute(self, **kwargs):
                return {"success": True}

        cmd = SimpleCommand(command_context)

        # Should still have access to tab and cdp
        assert cmd.tab is not None
        assert cmd.context is not None

    def test_to_mcp_tool_classmethod(self):
        """to_mcp_tool() should work without instance"""
        class TestCommand(Command):
            name = "test"
            description = "Test command"
            input_schema = {
                "type": "object",
                "properties": {
                    "param": {"type": "string"}
                }
            }

            async def execute(self, **kwargs):
                return {"success": True}

        # Call without creating instance
        tool = TestCommand.to_mcp_tool()

        assert tool["name"] == "test"
        assert tool["description"] == "Test command"
        assert tool["inputSchema"]["type"] == "object"
        assert "param" in tool["inputSchema"]["properties"]

    def test_execute_must_be_async(self, command_context):
        """execute() must be async"""
        import inspect

        class TestCommand(Command):
            name = "test"
            description = "Test"
            input_schema = {}

            async def execute(self, **kwargs):
                return {"success": True}

        cmd = TestCommand(command_context)

        assert inspect.iscoroutinefunction(cmd.execute)

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, command_context):
        """execute() should return dict"""
        class TestCommand(Command):
            name = "test"
            description = "Test"
            input_schema = {}

            async def execute(self, **kwargs):
                return {"success": True, "data": "test"}

        cmd = TestCommand(command_context)
        result = await cmd.execute()

        assert isinstance(result, dict)
        assert result["success"] is True

    def test_command_metadata_required(self):
        """Command metadata should be accessible through to_mcp_tool()"""
        # Command with None name should still work (validation happens at registration)
        class NoNameCommand(Command):
            # name = None (inherited from base)
            description = "Test"
            input_schema = {}

            async def execute(self, **kwargs):
                pass

        # to_mcp_tool() should work, returning None for missing name
        tool = NoNameCommand.to_mcp_tool()
        assert tool["name"] is None  # Will fail registration but not tool creation
        assert tool["description"] == "Test"


class TestCommandContext:
    """Test CommandContext dataclass"""

    def test_context_creation(self, mock_tab, mock_cursor, mock_browser, mock_async_cdp):
        """CommandContext should be created with all components"""
        from commands.context import CommandContext

        ctx = CommandContext(
            tab=mock_tab,
            cursor=mock_cursor,
            browser=mock_browser,
            cdp=mock_async_cdp
        )

        assert ctx.tab == mock_tab
        assert ctx.cursor == mock_cursor
        assert ctx.browser == mock_browser
        assert ctx.cdp == mock_async_cdp

    def test_context_optional_fields(self, mock_tab):
        """CommandContext should allow optional fields"""
        from commands.context import CommandContext

        ctx = CommandContext(tab=mock_tab)

        assert ctx.tab == mock_tab
        assert ctx.cursor is None
        assert ctx.browser is None
        assert ctx.cdp is None


class TestCommandDependencies:
    """Test dependency declaration system"""

    def test_requires_cursor_declaration(self, command_context):
        """Test requires_cursor dependency"""
        class CursorCommand(Command):
            name = "cursor_test"
            description = "Test"
            input_schema = {}
            requires_cursor = True

            async def execute(self, **kwargs):
                return {"success": True}

        cmd = CursorCommand(command_context)

        # Should have cursor injected
        assert cmd.cursor is not None

    def test_requires_browser_declaration(self, command_context):
        """Test requires_browser dependency"""
        class BrowserCommand(Command):
            name = "browser_test"
            description = "Test"
            input_schema = {}
            requires_browser = True

            async def execute(self, **kwargs):
                return {"success": True}

        cmd = BrowserCommand(command_context)

        # Should have browser injected
        assert cmd.browser is not None

    def test_multiple_dependencies(self, command_context):
        """Test multiple dependency declarations"""
        class MultiDepCommand(Command):
            name = "multi_test"
            description = "Test"
            input_schema = {}
            requires_cursor = True
            requires_browser = True

            async def execute(self, **kwargs):
                return {"success": True}

        cmd = MultiDepCommand(command_context)

        assert cmd.cursor is not None
        assert cmd.browser is not None
        assert cmd.cdp is not None
