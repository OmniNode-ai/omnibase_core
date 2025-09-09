"""
Node configuration utilities.

Utility functions for working with node configuration that follow
our architecture patterns and can be used by nodes via container injection.
"""

from typing import Optional

from omnibase_spi.protocols.core import ProtocolUtilsNodeConfiguration
from omnibase_spi.protocols.types.core_types import ContextValue

from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.model.config.model_node_configuration import ModelNodeConfiguration


class UtilsNodeConfiguration(ProtocolUtilsNodeConfiguration):
    """
    Utility class for node configuration access.

    Implements ProtocolUtilsNodeConfiguration to provide helper methods
    for nodes to access configuration injected via ModelONEXContainer
    without direct coupling.
    """

    def __init__(self, container: ModelONEXContainer):
        """Initialize with container for dependency injection."""
        self.container = container
        self._config: Optional[ModelNodeConfiguration] = None

    def get_configuration(self) -> ModelNodeConfiguration:
        """Get node configuration from container."""
        if self._config is None:
            # Try to get from container first, fallback to environment
            try:
                self._config = self.container.get_service("NodeConfiguration")
            except Exception:
                # Fallback to environment-based configuration
                self._config = ModelNodeConfiguration.from_environment()

        return self._config

    def get_timeout_ms(self, timeout_type: str, default_ms: int = 30000) -> int:
        """Get timeout configuration in milliseconds."""
        config = self.get_configuration()
        return config.get_timeout_ms(timeout_type, default_ms)

    def get_security_config(
        self, key: str, default: Optional[ContextValue] = None
    ) -> ContextValue:
        """Get security configuration value."""
        config = self.get_configuration()
        return config.get_security_config(key, default)

    def get_performance_config(
        self, key: str, default: Optional[ContextValue] = None
    ) -> ContextValue:
        """Get performance configuration value."""
        config = self.get_configuration()
        return config.get_performance_config(key, default)

    def get_business_logic_config(
        self, key: str, default: Optional[ContextValue] = None
    ) -> ContextValue:
        """Get business logic configuration value."""
        config = self.get_configuration()
        return config.get_business_logic_config(key, default)

    def validate_correlation_id(self, correlation_id: str) -> bool:
        """
        Validate correlation ID format using configuration.

        Args:
            correlation_id: Correlation ID to validate

        Returns:
            True if valid, False otherwise
        """
        if not correlation_id or not isinstance(correlation_id, str):
            return False

        config = self.get_configuration()

        # Check length constraints
        min_len = int(config.get_security_config("correlation_id_min_length", 8))
        max_len = int(config.get_security_config("correlation_id_max_length", 128))

        if len(correlation_id) < min_len or len(correlation_id) > max_len:
            return False

        # Check character constraints
        if not correlation_id.replace("-", "").replace("_", "").isalnum():
            return False

        return True
