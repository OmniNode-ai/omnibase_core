"""
ONEX Exception Classes

Standard exception hierarchy for ONEX architecture.
"""

from datetime import datetime
from typing import Any

from omnibase_core.models.core.model_onex_error import ModelOnexError


class OnexException(Exception):
    """
    Base exception for all ONEX-related errors.

    Provides structured error information with Pydantic model serialization.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """
        Initialize ONEX exception.

        Args:
            message: Human-readable error message
            error_code: Canonical ONEX error code
            context: Additional context information
            correlation_id: Request correlation ID for tracking
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.correlation_id = correlation_id
        self.timestamp = datetime.utcnow()

    def to_model(self) -> ModelOnexError:
        """Convert exception to Pydantic model."""
        from omnibase_core.models.core.model_error_context import ModelErrorContext

        return ModelOnexError(
            message=self.message,
            error_code=self.error_code,
            correlation_id=self.correlation_id,
            timestamp=self.timestamp,
            context=ModelErrorContext(properties=self.context),
        )


class OnexValidationException(OnexException):
    """Exception for validation errors."""

    def __init__(self, message: str, field_name: str | None = None, **kwargs) -> None:
        context = kwargs.get("context", {})
        if field_name:
            context["field_name"] = field_name
        kwargs["context"] = context

        super().__init__(message, **kwargs)


class OnexConfigurationException(OnexException):
    """Exception for configuration errors."""

    def __init__(self, message: str, config_path: str | None = None, **kwargs) -> None:
        context = kwargs.get("context", {})
        if config_path:
            context["config_path"] = config_path
        kwargs["context"] = context

        super().__init__(message, **kwargs)


class OnexContractException(OnexException):
    """Exception for contract-related errors."""

    def __init__(
        self,
        message: str,
        contract_path: str | None = None,
        node_name: str | None = None,
        **kwargs,
    ) -> None:
        context = kwargs.get("context", {})
        if contract_path:
            context["contract_path"] = contract_path
        if node_name:
            context["node_name"] = node_name
        kwargs["context"] = context

        super().__init__(message, **kwargs)


class OnexRegistryException(OnexException):
    """Exception for registry-related errors."""

    def __init__(
        self, message: str, registry_type: str | None = None, **kwargs
    ) -> None:
        context = kwargs.get("context", {})
        if registry_type:
            context["registry_type"] = registry_type
        kwargs["context"] = context

        super().__init__(message, **kwargs)
