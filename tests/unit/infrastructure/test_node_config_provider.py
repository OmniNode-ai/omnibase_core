# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for NodeConfigProvider implementation.

Tests ProtocolNodeConfiguration implementation with environment variable
support and fallback to defaults.

Test Coverage:
    - Configuration value retrieval
    - Environment variable overrides
    - Default value fallback
    - Type conversion
    - Configuration validation
    - Schema retrieval
"""

from typing import Any

import pytest

from omnibase_core.infrastructure.node_config_provider import NodeConfigProvider
from omnibase_core.models.configuration.model_node_config_value import (
    ModelNodeConfigSchema,
)


@pytest.mark.unit
class TestNodeConfigProviderBasics:
    """Test basic NodeConfigProvider functionality."""

    def test_initialization(self) -> None:
        """Test provider initialization."""
        provider = NodeConfigProvider()

        # Verify defaults are loaded
        assert provider._config_cache is not None
        assert len(provider._config_cache) > 0

    def test_has_default_configurations(self) -> None:
        """Test that all expected default configurations exist."""
        provider = NodeConfigProvider()

        # Compute node configurations
        assert provider.has_config("compute.max_parallel_workers")
        assert provider.has_config("compute.cache_ttl_minutes")
        assert provider.has_config("compute.performance_threshold_ms")

        # Effect node configurations
        assert provider.has_config("effect.default_timeout_ms")
        assert provider.has_config("effect.default_retry_delay_ms")
        assert provider.has_config("effect.max_concurrent_effects")

        # Reducer node configurations
        assert provider.has_config("reducer.default_batch_size")
        assert provider.has_config("reducer.max_memory_usage_mb")
        assert provider.has_config("reducer.streaming_buffer_size")

        # Orchestrator node configurations
        assert provider.has_config("orchestrator.max_concurrent_workflows")
        assert provider.has_config("orchestrator.default_step_timeout_ms")
        assert provider.has_config("orchestrator.action_emission_enabled")


@pytest.mark.unit
class TestNodeConfigProviderDefaults:
    """Test default value retrieval."""

    @pytest.mark.asyncio
    async def test_get_compute_defaults(self) -> None:
        """Test retrieving compute node defaults."""
        provider = NodeConfigProvider()

        max_workers = await provider.get_performance_config(
            "compute.max_parallel_workers"
        )
        assert max_workers == 4

        cache_ttl = await provider.get_performance_config("compute.cache_ttl_minutes")
        assert cache_ttl == 30

        perf_threshold = await provider.get_performance_config(
            "compute.performance_threshold_ms"
        )
        assert perf_threshold == 100.0

    @pytest.mark.asyncio
    async def test_get_effect_defaults(self) -> None:
        """Test retrieving effect node defaults."""
        provider = NodeConfigProvider()

        timeout = await provider.get_timeout_ms("effect.default_timeout_ms")
        assert timeout == 30000

        retry_delay = await provider.get_timeout_ms("effect.default_retry_delay_ms")
        assert retry_delay == 1000

        max_concurrent = await provider.get_performance_config(
            "effect.max_concurrent_effects"
        )
        assert max_concurrent == 10

    @pytest.mark.asyncio
    async def test_get_reducer_defaults(self) -> None:
        """Test retrieving reducer node defaults."""
        provider = NodeConfigProvider()

        batch_size = await provider.get_performance_config("reducer.default_batch_size")
        assert batch_size == 1000

        max_memory = await provider.get_performance_config(
            "reducer.max_memory_usage_mb"
        )
        assert max_memory == 512

        buffer_size = await provider.get_performance_config(
            "reducer.streaming_buffer_size"
        )
        assert buffer_size == 10000

    @pytest.mark.asyncio
    async def test_get_orchestrator_defaults(self) -> None:
        """Test retrieving orchestrator node defaults."""
        provider = NodeConfigProvider()

        max_workflows = await provider.get_performance_config(
            "orchestrator.max_concurrent_workflows"
        )
        assert max_workflows == 5

        step_timeout = await provider.get_timeout_ms(
            "orchestrator.default_step_timeout_ms"
        )
        assert step_timeout == 30000

        action_emission = await provider.get_business_logic_config(
            "orchestrator.action_emission_enabled"
        )
        assert action_emission is True


@pytest.mark.unit
class TestNodeConfigProviderEnvironmentOverrides:
    """Test environment variable override functionality."""

    def test_environment_variable_int_override(self, monkeypatch: Any) -> None:
        """Test overriding integer configuration with environment variable."""
        monkeypatch.setenv("ONEX_COMPUTE_MAX_PARALLEL_WORKERS", "8")
        provider = NodeConfigProvider()

        assert provider._config_cache["compute.max_parallel_workers"] == 8

    def test_environment_variable_float_override(self, monkeypatch: Any) -> None:
        """Test overriding float configuration with environment variable."""
        monkeypatch.setenv("ONEX_COMPUTE_PERFORMANCE_THRESHOLD_MS", "200.5")
        provider = NodeConfigProvider()

        assert provider._config_cache["compute.performance_threshold_ms"] == 200.5

    def test_environment_variable_bool_override_true(self, monkeypatch: Any) -> None:
        """Test overriding boolean configuration with environment variable (true)."""
        monkeypatch.setenv("ONEX_ORCHESTRATOR_ACTION_EMISSION_ENABLED", "true")
        provider = NodeConfigProvider()

        assert provider._config_cache["orchestrator.action_emission_enabled"] is True

    def test_environment_variable_bool_override_false(self, monkeypatch: Any) -> None:
        """Test overriding boolean configuration with environment variable (false)."""
        monkeypatch.setenv("ONEX_ORCHESTRATOR_ACTION_EMISSION_ENABLED", "false")
        provider = NodeConfigProvider()

        assert provider._config_cache["orchestrator.action_emission_enabled"] is False

    def test_environment_variable_bool_variations(self, monkeypatch: Any) -> None:
        """Test different boolean value variations."""
        # Test "1"
        monkeypatch.setenv("ONEX_ORCHESTRATOR_ACTION_EMISSION_ENABLED", "1")
        provider = NodeConfigProvider()
        assert provider._config_cache["orchestrator.action_emission_enabled"] is True

        # Test "yes"
        monkeypatch.setenv("ONEX_ORCHESTRATOR_ACTION_EMISSION_ENABLED", "yes")
        provider = NodeConfigProvider()
        assert provider._config_cache["orchestrator.action_emission_enabled"] is True

        # Test "on"
        monkeypatch.setenv("ONEX_ORCHESTRATOR_ACTION_EMISSION_ENABLED", "on")
        provider = NodeConfigProvider()
        assert provider._config_cache["orchestrator.action_emission_enabled"] is True

        # Test "0"
        monkeypatch.setenv("ONEX_ORCHESTRATOR_ACTION_EMISSION_ENABLED", "0")
        provider = NodeConfigProvider()
        assert provider._config_cache["orchestrator.action_emission_enabled"] is False

    @pytest.mark.asyncio
    async def test_environment_override_accessible_via_api(
        self, monkeypatch: Any
    ) -> None:
        """Test environment overrides are accessible via API methods."""
        monkeypatch.setenv("ONEX_COMPUTE_MAX_PARALLEL_WORKERS", "16")
        provider = NodeConfigProvider()

        max_workers = await provider.get_performance_config(
            "compute.max_parallel_workers"
        )
        assert max_workers == 16


@pytest.mark.unit
class TestNodeConfigProviderCustomDefaults:
    """Test custom default value handling."""

    @pytest.mark.asyncio
    async def test_get_config_with_custom_default(self) -> None:
        """Test retrieving config with custom default for missing key."""
        provider = NodeConfigProvider()

        value = await provider.get_config_value("nonexistent.key", "custom_default")
        assert value == "custom_default"

    @pytest.mark.asyncio
    async def test_get_timeout_with_custom_default(self) -> None:
        """Test retrieving timeout with custom default for missing key."""
        provider = NodeConfigProvider()

        timeout = await provider.get_timeout_ms("nonexistent.timeout", 5000)
        assert timeout == 5000

    @pytest.mark.asyncio
    async def test_get_performance_config_with_custom_default(self) -> None:
        """Test retrieving performance config with custom default."""
        provider = NodeConfigProvider()

        value = await provider.get_performance_config("nonexistent.perf", 999)
        assert value == 999

    @pytest.mark.asyncio
    async def test_timeout_fallback_to_30_seconds(self) -> None:
        """Test timeout defaults to 30 seconds when no default provided."""
        provider = NodeConfigProvider()

        timeout = await provider.get_timeout_ms("nonexistent.timeout")
        assert timeout == 30000


@pytest.mark.unit
class TestNodeConfigProviderValidation:
    """Test configuration validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_existing_config(self) -> None:
        """Test validating existing configuration key."""
        provider = NodeConfigProvider()

        is_valid = await provider.validate_config("compute.max_parallel_workers")
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_nonexistent_config(self) -> None:
        """Test validating nonexistent configuration key."""
        provider = NodeConfigProvider()

        is_valid = await provider.validate_config("nonexistent.key")
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_required_configs_all_present(self) -> None:
        """Test validating multiple required configs (all present)."""
        provider = NodeConfigProvider()

        required_keys = [
            "compute.max_parallel_workers",
            "effect.default_timeout_ms",
            "reducer.default_batch_size",
        ]

        results = await provider.validate_required_configs(required_keys)

        assert results["compute.max_parallel_workers"] is True
        assert results["effect.default_timeout_ms"] is True
        assert results["reducer.default_batch_size"] is True

    @pytest.mark.asyncio
    async def test_validate_required_configs_some_missing(self) -> None:
        """Test validating multiple required configs (some missing)."""
        provider = NodeConfigProvider()

        required_keys = [
            "compute.max_parallel_workers",
            "nonexistent.key",
            "reducer.default_batch_size",
        ]

        results = await provider.validate_required_configs(required_keys)

        assert results["compute.max_parallel_workers"] is True
        assert results["nonexistent.key"] is False
        assert results["reducer.default_batch_size"] is True


@pytest.mark.unit
class TestNodeConfigProviderSchema:
    """Test configuration schema functionality."""

    @pytest.mark.asyncio
    async def test_get_config_schema(self) -> None:
        """Test retrieving configuration schema."""
        provider = NodeConfigProvider()

        schema = await provider.get_config_schema()

        assert isinstance(schema, dict)
        assert len(schema) > 0

        # Verify schema contains expected keys
        assert "compute.max_parallel_workers" in schema
        assert "effect.default_timeout_ms" in schema
        assert "reducer.default_batch_size" in schema
        assert "orchestrator.max_concurrent_workflows" in schema

    @pytest.mark.asyncio
    async def test_schema_structure(self) -> None:
        """Test schema entry structure."""
        provider = NodeConfigProvider()

        schema = await provider.get_config_schema()

        # Check structure of a schema entry
        compute_workers_schema = schema["compute.max_parallel_workers"]
        # Schema entries are now ModelNodeConfigSchema Pydantic models
        assert isinstance(compute_workers_schema, ModelNodeConfigSchema)
        assert hasattr(compute_workers_schema, "key")
        assert hasattr(compute_workers_schema, "config_type")
        assert hasattr(compute_workers_schema, "default")

        # Verify values
        assert compute_workers_schema.key == "compute.max_parallel_workers"
        assert compute_workers_schema.config_type == "int"
        assert compute_workers_schema.default == 4


@pytest.mark.unit
class TestNodeConfigProviderAllConfig:
    """Test retrieving all configuration."""

    @pytest.mark.asyncio
    async def test_get_all_config(self) -> None:
        """Test retrieving all configuration as dictionary."""
        provider = NodeConfigProvider()

        all_config = await provider.get_all_config()

        assert isinstance(all_config, dict)
        assert len(all_config) > 0

        # Verify all defaults are present
        assert "compute.max_parallel_workers" in all_config
        assert "effect.default_timeout_ms" in all_config
        assert "reducer.default_batch_size" in all_config
        assert "orchestrator.max_concurrent_workflows" in all_config

    @pytest.mark.asyncio
    async def test_get_all_config_includes_overrides(self, monkeypatch: Any) -> None:
        """Test that get_all_config includes environment overrides."""
        monkeypatch.setenv("ONEX_COMPUTE_MAX_PARALLEL_WORKERS", "32")
        provider = NodeConfigProvider()

        all_config = await provider.get_all_config()

        assert all_config["compute.max_parallel_workers"] == 32


@pytest.mark.unit
class TestNodeConfigProviderTypeConversion:
    """Test type conversion in get_timeout_ms."""

    @pytest.mark.asyncio
    async def test_timeout_converts_float_to_int(self) -> None:
        """Test that get_timeout_ms converts float to int."""
        provider = NodeConfigProvider()

        # Manually set a float value in cache
        provider._config_cache["test.timeout"] = 5000.7

        timeout = await provider.get_timeout_ms("test.timeout")
        assert isinstance(timeout, int)
        assert timeout == 5000

    @pytest.mark.asyncio
    async def test_timeout_handles_int_directly(self) -> None:
        """Test that get_timeout_ms handles int values."""
        provider = NodeConfigProvider()

        timeout = await provider.get_timeout_ms("effect.default_timeout_ms")
        assert isinstance(timeout, int)
        assert timeout == 30000


@pytest.mark.unit
class TestNodeConfigProviderDomainMethods:
    """Test domain-specific configuration methods."""

    @pytest.mark.asyncio
    async def test_get_security_config(self) -> None:
        """Test getting security configuration."""
        provider = NodeConfigProvider()

        # Security config falls back to general config
        value = await provider.get_security_config("compute.max_parallel_workers")
        assert value == 4

        # With custom default
        value = await provider.get_security_config("nonexistent.security", "secure")
        assert value == "secure"

    @pytest.mark.asyncio
    async def test_get_business_logic_config(self) -> None:
        """Test getting business logic configuration."""
        provider = NodeConfigProvider()

        value = await provider.get_business_logic_config(
            "orchestrator.action_emission_enabled"
        )
        assert value is True

        # With custom default
        value = await provider.get_business_logic_config("nonexistent.logic", False)
        assert value is False

    @pytest.mark.asyncio
    async def test_get_performance_config(self) -> None:
        """Test getting performance configuration."""
        provider = NodeConfigProvider()

        value = await provider.get_performance_config("compute.max_parallel_workers")
        assert value == 4

        # With custom default
        value = await provider.get_performance_config("nonexistent.perf", 100)
        assert value == 100
