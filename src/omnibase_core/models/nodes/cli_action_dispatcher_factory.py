"""
CLI Action Dispatcher Factory.

Factory for creating CLI action dispatchers with different configurations.
"""

from omnibase_core.models.nodes.cli_action_dispatcher import CliActionDispatcher
from omnibase_core.models.nodes.cli_command_registry import CliCommandRegistry


class CliActionDispatcherFactory:
    """
    Factory for creating CLI action dispatchers.

    Provides different dispatcher configurations for different use cases.
    """

    @staticmethod
    def create_default_dispatcher() -> CliActionDispatcher:
        """
        Create dispatcher with default configuration.

        Returns:
            Default CLI action dispatcher
        """
        return CliActionDispatcher()

    @staticmethod
    def create_custom_dispatcher(
        command_registry: CliCommandRegistry,
    ) -> CliActionDispatcher:
        """
        Create dispatcher with custom command registry.

        Args:
            command_registry: Custom command registry

        Returns:
            CLI action dispatcher with custom registry
        """
        return CliActionDispatcher(command_registry)

    @staticmethod
    def create_minimal_dispatcher() -> CliActionDispatcher:
        """
        Create dispatcher with minimal command set.

        Returns:
            Minimal CLI action dispatcher
        """
        # Create registry with only essential commands
        minimal_registry = CliCommandRegistry()
        minimal_registry.reset_to_defaults()

        # Could remove some commands here if needed for minimal setup
        return CliActionDispatcher(minimal_registry)


# Export for use
__all__ = [
    "CliActionDispatcherFactory",
]