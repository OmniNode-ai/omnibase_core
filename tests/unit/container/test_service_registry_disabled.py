"""Unit tests for ServiceRegistry disabled error paths.

Tests error handling when ServiceRegistry is disabled in ModelONEXContainer.
"""

from typing import Any
from uuid import UUID

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.container.model_onex_container import (
    ModelONEXContainer,
    create_model_onex_container,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


# Test Protocol Interface for service resolution
class ITestProtocol:
    """Test protocol interface for testing service resolution."""

    def execute(self) -> str:
        """Execute service logic."""
        raise NotImplementedError


def get_nested_context(error: ModelOnexError) -> dict[str, Any]:
    """Extract the actual context dict from nested error structure.

    ModelOnexError stores context in a nested structure:
    {'additional_context': {'context': {actual context}}}
    """
    context = error.context or {}
    if "additional_context" in context:
        additional = context.get("additional_context", {})
        if isinstance(additional, dict) and "context" in additional:
            return additional.get("context", {})
    return context


@pytest.mark.unit
class TestServiceRegistryDisabledErrorPath:
    """Test error handling when ServiceRegistry is disabled."""

    @pytest.mark.asyncio
    async def test_get_service_async_raises_error_when_registry_disabled(self) -> None:
        """Test that get_service_async raises ModelOnexError when ServiceRegistry is disabled.

        When enable_service_registry=False, any attempt to resolve a service
        should fail with DEPENDENCY_UNAVAILABLE error code.
        """
        # Create container with ServiceRegistry disabled
        container = await create_model_onex_container(enable_service_registry=False)

        # Verify registry is None
        assert container.service_registry is None

        # Attempt to resolve a service - should raise ModelOnexError
        with pytest.raises(ModelOnexError) as exc_info:
            await container.get_service_async(ITestProtocol)

        # Verify error details
        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE
        assert "ServiceRegistry is disabled" in error.message
        assert "ITestProtocol" in error.message

        # Verify context contains expected information (from nested structure)
        nested_context = get_nested_context(error)
        assert nested_context.get("protocol_type") == "ITestProtocol"
        assert "hint" in nested_context

    @pytest.mark.asyncio
    async def test_get_service_async_with_service_name_when_registry_disabled(
        self,
    ) -> None:
        """Test that service name is included in error context when registry is disabled."""
        container = await create_model_onex_container(enable_service_registry=False)

        with pytest.raises(ModelOnexError) as exc_info:
            await container.get_service_async(
                ITestProtocol, service_name="custom_service"
            )

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE
        nested_context = get_nested_context(error)
        # Service name should be in context
        assert nested_context.get("service_name") == "custom_service"

    @pytest.mark.asyncio
    async def test_get_service_optional_returns_none_when_registry_disabled(
        self,
    ) -> None:
        """Test that get_service_optional returns None when registry is disabled.

        get_service_optional should catch the ModelOnexError and return None
        instead of raising.
        """
        container = await create_model_onex_container(enable_service_registry=False)

        # get_service_optional should return None, not raise
        result = container.get_service_optional(ITestProtocol)

        assert result is None

    def test_sync_container_init_with_registry_disabled(self) -> None:
        """Test that ModelONEXContainer can be initialized with registry disabled."""
        container = ModelONEXContainer(enable_service_registry=False)

        assert container.service_registry is None
        assert container._enable_service_registry is False

    @pytest.mark.asyncio
    async def test_error_includes_correlation_id(self) -> None:
        """Test that error has a correlation ID for tracing.

        The error should have a correlation_id property that is a valid UUID.
        """
        container = await create_model_onex_container(enable_service_registry=False)

        with pytest.raises(ModelOnexError) as exc_info:
            await container.get_service_async(ITestProtocol)

        error = exc_info.value

        # Correlation ID should be available as a property on the error
        correlation_id = error.correlation_id
        assert correlation_id is not None
        assert isinstance(correlation_id, UUID)
