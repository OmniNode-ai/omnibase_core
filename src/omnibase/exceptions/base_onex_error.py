"""
Base OnexError exception class.

Extracted from core_error_codes.py to eliminate circular import issues
while maintaining full backward compatibility.
"""

import sys
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional, Union

from omnibase.enums.enum_onex_status import EnumOnexStatus

if TYPE_CHECKING:
    # Import only for type checking to avoid circular imports
    from omnibase.core.core_error_codes import OnexErrorCode


class OnexError(Exception):
    """
    Exception class for ONEX errors with Pydantic model integration.

    This class combines standard Python exception behavior with Pydantic
    model features through composition, providing validation, serialization,
    and schema generation while maintaining exception compatibility.

    All ONEX nodes should use this or subclasses for error handling
    to ensure consistent error reporting and CLI exit code mapping.
    """

    def __init__(
        self,
        message: str,
        error_code: Union["OnexErrorCode", str, None] = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        correlation_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        **context: str,
    ) -> None:
        """
        Initialize an ONEX error with error code and status.

        Args:
            message: Human-readable error message
            error_code: Canonical error code (optional)
            status: OnexStatus for this error (default: ERROR)
            correlation_id: Optional correlation ID for request tracking
            timestamp: Optional timestamp (defaults to current time)
            **context: Additional context information
        """
        # Initialize the Exception
        super().__init__(message)

        # Create the Pydantic model for structured data
        # Import locally to avoid circular import
        from omnibase.model.core.model_onex_error import ModelOnexError

        self.model = ModelOnexError(
            message=message,
            error_code=error_code,
            status=status,
            correlation_id=correlation_id,
            timestamp=timestamp or datetime.utcnow(),
            context=context,
        )

    @property
    def message(self) -> str:
        """Get the error message."""
        return str(self.model.message)

    @property
    def error_code(self) -> Optional[Union[str, "OnexErrorCode"]]:
        """Get the error code."""
        error_code = self.model.error_code
        if error_code is None:
            return None
        if isinstance(error_code, (str,)):
            return error_code
        # Import locally to check instance without circular import
        try:
            from omnibase.core.core_error_codes import OnexErrorCode

            if isinstance(error_code, OnexErrorCode):
                return error_code
        except ImportError:
            pass
        return str(error_code)

    @property
    def status(self) -> EnumOnexStatus:
        """Get the error status."""
        return self.model.status

    @property
    def correlation_id(self) -> Optional[str]:
        """Get the correlation ID."""
        correlation_id = self.model.correlation_id
        return str(correlation_id) if correlation_id is not None else None

    @property
    def timestamp(self) -> Optional[datetime]:
        """Get the timestamp."""
        timestamp = self.model.timestamp
        if isinstance(timestamp, datetime):
            return timestamp
        return None

    @property
    def context(self) -> Dict[str, str]:
        """Get the context information."""
        context = self.model.context
        if isinstance(context, dict):
            # Convert all context values to strings for consistent typing
            return {k: str(v) for k, v in context.items() if v is not None}
        return {}

    def get_exit_code(self) -> int:
        """Get the appropriate CLI exit code for this error."""
        # Import locally to avoid circular imports
        from omnibase.core.core_error_codes import (
            OnexErrorCode,
            get_exit_code_for_status,
        )

        if isinstance(self.error_code, OnexErrorCode):
            return self.error_code.get_exit_code()
        return get_exit_code_for_status(self.status)

    def __str__(self) -> str:
        """String representation including error code if available."""
        if self.error_code:
            # Use .value to get the string value for OnexErrorCode enums
            error_code_str = (
                self.error_code.value
                if hasattr(self.error_code, "value")
                else str(self.error_code)
            )
            return f"[{error_code_str}] {self.message}"
        return self.message

    def model_dump(self) -> "ModelErrorSerializationData":
        """Convert error to strongly typed serialization model."""
        # Get original context from the model to preserve types
        original_context = self.model.context if hasattr(self.model, "context") else {}

        # Separate context by type
        context_strings = {}
        context_numbers = {}
        context_flags = {}

        for k, v in original_context.items():
            if isinstance(v, str):
                context_strings[k] = v
            elif isinstance(v, (int, float)):
                context_numbers[k] = int(v)
            elif isinstance(v, bool):
                context_flags[k] = v

        # Import locally to avoid circular imports
        from omnibase.model.core.model_error_serialization_data import (
            ModelErrorSerializationData,
        )

        return ModelErrorSerializationData(
            message=str(self.message),
            error_code=str(self.error_code) if self.error_code else None,
            status=self.status,
            correlation_id=self.correlation_id,
            timestamp=self.timestamp,
            context_strings=context_strings,
            context_numbers=context_numbers,
            context_flags=context_flags,
        )

    def model_dump_json(self) -> str:
        """Convert error to JSON string for logging/telemetry."""
        result = self.model.model_dump_json()
        return str(result)

    def to_dict(self) -> "ModelErrorSerializationData":
        """Convert error to strongly typed serialization model (alias for model_dump)."""
        return self.model_dump()

    def to_json(self) -> str:
        """Convert error to JSON string for logging/telemetry (alias for model_dump_json)."""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: "ModelErrorSerializationData") -> "OnexError":
        """Create OnexError from dictionary."""
        return cls(
            message=data.message,
            error_code=data.error_code,
            status=data.status,
            correlation_id=data.correlation_id,
            timestamp=data.timestamp,
            **data.context_strings,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "OnexError":
        """Create OnexError from JSON string."""
        # Import locally to avoid circular import
        from omnibase.model.core.model_onex_error import ModelOnexError

        model = ModelOnexError.model_validate_json(json_str)
        return cls(
            message=model.message,
            error_code=model.error_code,
            status=model.status,
            correlation_id=model.correlation_id,
            timestamp=model.timestamp,
            **model.context,
        )

    @classmethod
    def model_json_schema(cls) -> "ModelErrorJsonSchema":
        """Get the JSON schema for OnexError as a strongly typed model."""
        # Import locally to avoid circular imports
        from omnibase.model.core.model_error_json_schema import ModelErrorJsonSchema

        return ModelErrorJsonSchema(
            schema_type="object",
            properties={
                "message": {"type": "string", "description": "Error message"},
                "error_code": {"type": "string", "description": "Error code"},
                "status": {"type": "string", "description": "Error status"},
                "correlation_id": {"type": "string", "description": "Correlation ID"},
                "timestamp": {"type": "string", "description": "Error timestamp"},
            },
            required_fields=["message", "status"],
        )
