"""
Node configuration provider implementation for ONEX architecture.

Implements ProtocolNodeConfiguration to provide externalized configuration
for all ONEX nodes with environment variable support and sensible defaults.

Domain: Infrastructure configuration management
"""

import os

from omnibase_core.constants import TIMEOUT_DEFAULT_MS
from omnibase_core.models.configuration.model_node_config_value import (
    ModelNodeConfigSchema,
    ScalarConfigValue,
    is_valid_value_type,
)


class NodeConfigProvider:
    """
    Configuration provider for ONEX nodes.

    Implements ProtocolNodeConfiguration to externalize node configurations
    from environment variables with fallback to sensible defaults.

    Key Features:
        - Environment variable-based configuration
        - Sensible defaults for all configuration values
        - Type-safe configuration access
        - Domain-specific configuration methods

    Configuration Keys:
        Performance:
            - compute.max_parallel_workers: Max parallel workers for compute nodes
            - compute.cache_ttl_minutes: Cache TTL in minutes for compute nodes
            - compute.performance_threshold_ms: Performance threshold in milliseconds
            - effect.max_concurrent_effects: Max concurrent effects for effect nodes
            - reducer.default_batch_size: Default batch size for reducer nodes
            - reducer.max_memory_usage_mb: Max memory usage in MB for reducer nodes
            - reducer.streaming_buffer_size: Streaming buffer size for reducer nodes
            - orchestrator.max_concurrent_workflows: Max concurrent workflows
            - orchestrator.action_emission_enabled: Enable action emission

        Timeouts:
            - effect.default_timeout_ms: Default timeout for effect operations
            - effect.default_retry_delay_ms: Default retry delay for effects
            - orchestrator.default_step_timeout_ms: Default step timeout for orchestrator

    Environment Variables:
        - ONEX_<KEY>: Override any configuration (e.g., ONEX_COMPUTE_MAX_PARALLEL_WORKERS=8)
        - Keys use uppercase with underscores (dots become underscores)

    Example:
        ```python
        config = NodeConfigProvider()

        # Get performance configuration
        max_workers = await config.get_performance_config(
            "compute.max_parallel_workers", 4
        )

        # Get timeout configuration
        timeout = await config.get_timeout_ms("effect.default_timeout", TIMEOUT_DEFAULT_MS)

        # Get general configuration
        cache_ttl = await config.get_config_value("compute.cache_ttl_minutes", 30)
        ```
    """

    # Default configuration values
    _DEFAULTS: dict[str, ScalarConfigValue] = {
        # Compute node defaults
        "compute.max_parallel_workers": 4,
        "compute.cache_ttl_minutes": 30,
        "compute.performance_threshold_ms": 100.0,
        # Effect node defaults
        "effect.default_timeout_ms": TIMEOUT_DEFAULT_MS,
        "effect.default_retry_delay_ms": 1000,
        "effect.max_concurrent_effects": 10,
        # Reducer node defaults
        "reducer.default_batch_size": 1000,
        "reducer.max_memory_usage_mb": 512,
        "reducer.streaming_buffer_size": 10000,
        # Orchestrator node defaults
        "orchestrator.max_concurrent_workflows": 5,
        "orchestrator.default_step_timeout_ms": TIMEOUT_DEFAULT_MS,
        "orchestrator.action_emission_enabled": True,
    }

    def __init__(self) -> None:
        """Initialize configuration provider."""
        self._config_cache: dict[str, ScalarConfigValue] = {}
        self._load_environment_config()

    def _load_environment_config(self) -> None:
        """Load configuration from environment variables."""
        # Load all ONEX_* environment variables
        for key, default_value in self._DEFAULTS.items():
            env_key = f"ONEX_{key.upper().replace('.', '_')}"
            env_value = os.environ.get(env_key)

            if env_value is not None:
                # Convert environment variable to appropriate type
                if isinstance(default_value, bool):
                    self._config_cache[key] = env_value.lower() in (
                        "true",
                        "1",
                        "yes",
                        "on",
                    )
                elif isinstance(default_value, int):
                    self._config_cache[key] = int(env_value)
                elif isinstance(default_value, float):
                    self._config_cache[key] = float(env_value)
                else:
                    self._config_cache[key] = env_value
            else:
                # Use default value
                self._config_cache[key] = default_value

    async def get_config_value(
        self, key: str, default: ScalarConfigValue | None = None
    ) -> ScalarConfigValue | None:
        """
        Get configuration value by key.

        Args:
            key: Configuration key (e.g., "compute.max_parallel_workers")
            default: Optional default value if key not found

        Returns:
            Configuration value or default
        """
        if key in self._config_cache:
            return self._config_cache[key]

        if default is not None:
            return default

        # Return from defaults if available
        if key in self._DEFAULTS:
            return self._DEFAULTS[key]

        # Return None if no default provided
        return None

    async def get_timeout_ms(
        self, timeout_type: str, default_ms: int | None = None
    ) -> int:
        """
        Get timeout configuration in milliseconds.

        Args:
            timeout_type: Timeout type key (e.g., "effect.default_timeout")
            default_ms: Optional default timeout in milliseconds

        Returns:
            Timeout value in milliseconds
        """
        value = await self.get_config_value(timeout_type, default_ms)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if default_ms is not None:
            return default_ms
        return TIMEOUT_DEFAULT_MS  # Default 30 seconds

    async def get_security_config(
        self, key: str, default: ScalarConfigValue | None = None
    ) -> ScalarConfigValue | None:
        """
        Get security-related configuration.

        Args:
            key: Security configuration key
            default: Optional default value

        Returns:
            Security configuration value
        """
        return await self.get_config_value(key, default)

    async def get_business_logic_config(
        self, key: str, default: ScalarConfigValue | None = None
    ) -> ScalarConfigValue | None:
        """
        Get business logic configuration.

        Args:
            key: Business logic configuration key
            default: Optional default value

        Returns:
            Business logic configuration value
        """
        return await self.get_config_value(key, default)

    async def get_performance_config(
        self, key: str, default: ScalarConfigValue | None = None
    ) -> ScalarConfigValue | None:
        """
        Get performance-related configuration.

        Args:
            key: Performance configuration key
            default: Optional default value

        Returns:
            Performance configuration value
        """
        return await self.get_config_value(key, default)

    def has_config(self, key: str) -> bool:
        """
        Check if configuration key exists.

        Args:
            key: Configuration key to check

        Returns:
            True if key exists in configuration
        """
        return key in self._config_cache or key in self._DEFAULTS

    async def get_all_config(self) -> dict[str, ScalarConfigValue]:
        """
        Get all configuration as dictionary.

        Returns:
            Dictionary of all configuration values
        """
        return dict(self._config_cache)

    async def validate_config(self, config_key: str) -> bool:
        """
        Validate specific configuration key.

        Args:
            config_key: Configuration key to validate

        Returns:
            True if configuration is valid
        """
        return self.has_config(config_key)

    async def validate_required_configs(
        self, required_keys: list[str]
    ) -> dict[str, bool]:
        """
        Validate multiple required configuration keys.

        Args:
            required_keys: List of required configuration keys

        Returns:
            Dictionary mapping keys to validation status
        """
        return {key: self.has_config(key) for key in required_keys}

    async def get_config_schema(self) -> dict[str, ModelNodeConfigSchema]:
        """
        Get configuration schema.

        Returns:
            Dictionary describing configuration schema
        """
        schema: dict[str, ModelNodeConfigSchema] = {}
        for key, value in self._DEFAULTS.items():
            type_name = type(value).__name__
            # Type guard validates and narrows type_name to VALID_VALUE_TYPES
            if not is_valid_value_type(type_name):
                raise ValueError(  # error-ok: internal bootstrap validation before OnexError available
                    f"Invalid config type '{type_name}' for key '{key}'. "
                    f"Allowed types: ('int', 'float', 'bool', 'str')"
                )
            schema[key] = ModelNodeConfigSchema(
                key=key,
                type=type_name,
                default=value,
            )
        return schema
