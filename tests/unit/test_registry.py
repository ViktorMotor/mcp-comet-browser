"""
Unit tests for commands/registry.py - Auto-discovery system
"""
import pytest
from commands.registry import CommandRegistry, register
from commands.base import Command
from typing import Dict, Any


# Module-level setup: discover all commands once
def setup_module():
    """Discover all commands before running tests"""
    CommandRegistry.discover_commands()


class TestCommandRegistry:
    """Test command registration and auto-discovery"""

    def test_registry_exists(self):
        """Registry should be initialized"""
        registry = CommandRegistry.get_all_commands()
        assert registry is not None
        assert isinstance(registry, dict)

    def test_registry_contains_commands(self):
        """Registry should contain registered commands"""
        registry = CommandRegistry.get_all_commands()
        # Should have 29 commands registered
        assert len(registry) >= 20  # At least 20 commands

    def test_registry_command_names(self):
        """Registry should contain expected command names"""
        registry = CommandRegistry.get_all_commands()
        expected_commands = [
            'open_url',
            'get_text',
            'click',
            'click_by_text',
            'scroll_page',
            'move_cursor',
            'screenshot',
            'evaluate_js',
            'save_page_info',
            'list_tabs',
            'create_tab',
            'close_tab',
            'switch_tab'
        ]

        for cmd_name in expected_commands:
            assert cmd_name in registry, f"Command '{cmd_name}' not found in registry"

    def test_registry_command_classes(self):
        """All registered commands should be Command subclasses"""
        registry = CommandRegistry.get_all_commands()
        for cmd_name, cmd_class in registry.items():
            assert issubclass(cmd_class, Command), f"{cmd_name} is not a Command subclass"

    def test_registry_command_metadata(self):
        """All commands should have required metadata"""
        registry = CommandRegistry.get_all_commands()
        for cmd_name, cmd_class in registry.items():
            # Check class attributes exist
            assert hasattr(cmd_class, 'name'), f"{cmd_name} missing 'name' attribute"
            assert hasattr(cmd_class, 'description'), f"{cmd_name} missing 'description' attribute"
            assert hasattr(cmd_class, 'input_schema'), f"{cmd_name} missing 'input_schema' attribute"

            # Check metadata values
            assert cmd_class.name == cmd_name, f"Command name mismatch: {cmd_class.name} != {cmd_name}"
            assert len(cmd_class.description) > 0, f"{cmd_name} has empty description"
            assert isinstance(cmd_class.input_schema, dict), f"{cmd_name} input_schema is not dict"

    def test_register_decorator(self):
        """@register decorator should add command to registry"""
        # Create test command
        @register
        class TestCommand(Command):
            name = "test_command_xyz"
            description = "Test command"
            input_schema = {"type": "object", "properties": {}}

            async def execute(self, **kwargs) -> Dict[str, Any]:
                return {"success": True}

        # Should be in registry
        registry = CommandRegistry.get_all_commands()
        assert "test_command_xyz" in registry
        assert registry["test_command_xyz"] == TestCommand

        # Cleanup
        CommandRegistry._commands.pop("test_command_xyz", None)

    def test_register_without_name(self):
        """@register should fail if command has no name"""
        with pytest.raises(ValueError, match="must define 'name' class attribute"):
            @register
            class BadCommand(Command):
                description = "Missing name"
                input_schema = {}

                async def execute(self, **kwargs):
                    pass

    def test_get_command(self):
        """Test getting command by name"""
        cmd_class = CommandRegistry.get_command('open_url')
        assert cmd_class is not None
        assert cmd_class.name == 'open_url'

    def test_get_command_not_found(self):
        """Test getting non-existent command"""
        with pytest.raises(KeyError, match="not registered"):
            CommandRegistry.get_command('nonexistent_command')

    def test_to_mcp_tool_is_classmethod(self):
        """Command.to_mcp_tool() should be callable without instance"""
        # Get any command from registry
        cmd_class = CommandRegistry.get_command('open_url')

        # Should be callable as classmethod
        tool = cmd_class.to_mcp_tool()

        assert isinstance(tool, dict)
        assert 'name' in tool
        assert 'description' in tool
        assert 'inputSchema' in tool

    def test_command_has_execute_method(self):
        """All commands should have async execute method"""
        import inspect

        registry = CommandRegistry.get_all_commands()
        for cmd_name, cmd_class in registry.items():
            assert hasattr(cmd_class, 'execute'), f"{cmd_name} missing 'execute' method"
            execute_method = getattr(cmd_class, 'execute')
            assert inspect.iscoroutinefunction(execute_method), f"{cmd_name}.execute is not async"


class TestCommandMetadata:
    """Test Command metadata as class attributes"""

    def test_metadata_not_properties(self):
        """Metadata should be class attributes, not @property"""
        from commands.navigation import OpenUrlCommand

        # Should be class attributes (not properties)
        assert not isinstance(OpenUrlCommand.__dict__.get('name'), property)
        assert not isinstance(OpenUrlCommand.__dict__.get('description'), property)
        assert not isinstance(OpenUrlCommand.__dict__.get('input_schema'), property)

    def test_to_mcp_tool_no_instance_needed(self):
        """to_mcp_tool() should not require Command instance"""
        from commands.navigation import OpenUrlCommand

        # Should work without creating instance
        tool = OpenUrlCommand.to_mcp_tool()

        assert tool['name'] == 'open_url'
        assert 'description' in tool
        assert 'inputSchema' in tool
        assert isinstance(tool['inputSchema'], dict)

    def test_dependency_declarations(self):
        """Commands should declare dependencies via class attributes"""
        from commands.interaction import ClickCommand
        from commands.navigation import OpenUrlCommand

        # ClickCommand requires cursor
        assert hasattr(ClickCommand, 'requires_cursor')
        assert ClickCommand.requires_cursor is True

        # OpenUrlCommand requires cursor and cdp
        assert hasattr(OpenUrlCommand, 'requires_cursor')
        assert hasattr(OpenUrlCommand, 'requires_cdp')
