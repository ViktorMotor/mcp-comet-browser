"""
Command registry for automatic command discovery.

Provides @register decorator for auto-discovery of browser commands,
eliminating manual registration in protocol.py.
"""

from typing import Dict, Type, List
import importlib
import pkgutil
from mcp.logging_config import get_logger

logger = get_logger("commands.registry")


class CommandRegistry:
    """
    Global registry for browser commands.

    Commands self-register using @register decorator.
    Supports automatic module discovery and import.
    """

    _commands: Dict[str, Type] = {}

    @classmethod
    def register(cls, command_class: Type) -> Type:
        """
        Register a command class.

        Usage:
            @CommandRegistry.register
            class MyCommand(Command):
                name = "my_command"
                ...

        Args:
            command_class: Command class to register

        Returns:
            The same command class (decorator passthrough)
        """
        if not hasattr(command_class, 'name') or command_class.name is None:
            raise ValueError(f"Command {command_class.__name__} must define 'name' class attribute")

        name = command_class.name
        if name in cls._commands:
            logger.warning(f"Command '{name}' already registered, overwriting with {command_class.__name__}")

        cls._commands[name] = command_class
        logger.debug(f"Registered command: {name} ({command_class.__name__})")

        return command_class

    @classmethod
    def get_command(cls, name: str) -> Type:
        """
        Get command class by name.

        Args:
            name: Command name

        Returns:
            Command class

        Raises:
            KeyError: If command not found
        """
        if name not in cls._commands:
            raise KeyError(f"Command '{name}' not registered")
        return cls._commands[name]

    @classmethod
    def get_all_commands(cls) -> Dict[str, Type]:
        """
        Get all registered commands.

        Returns:
            Dict mapping command names to command classes
        """
        return cls._commands.copy()

    @classmethod
    def discover_commands(cls, package_name: str = 'commands'):
        """
        Automatically discover and import all command modules.

        Imports all Python modules in the commands package,
        triggering @register decorators.

        Args:
            package_name: Package to scan for command modules
        """
        try:
            # Import the package
            package = importlib.import_module(package_name)

            # Get package path
            if not hasattr(package, '__path__'):
                logger.warning(f"Package {package_name} has no __path__, skipping discovery")
                return

            # Discover all modules in package
            module_names = []
            for finder, name, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
                if not ispkg:  # Only import modules, not sub-packages
                    module_names.append(name)

            # Import each module
            logger.debug(f"Discovering commands in {len(module_names)} modules")
            for module_name in module_names:
                try:
                    importlib.import_module(module_name)
                    logger.debug(f"Imported module: {module_name}")
                except Exception as e:
                    logger.error(f"Failed to import {module_name}: {e}")

            logger.info(f"Command discovery complete: {len(cls._commands)} commands registered")

        except Exception as e:
            logger.error(f"Failed to discover commands: {e}")
            raise

    @classmethod
    def clear(cls):
        """Clear all registered commands (useful for testing)"""
        cls._commands.clear()
        logger.debug("Command registry cleared")


# Convenience decorator alias
register = CommandRegistry.register
