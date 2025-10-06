import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import Field

from omnibase_core.errors.error_codes import ModelCoreErrorCode, ModelOnexError

"""
ONEX Error Base Class

Base exception class for all ONEX errors with Pydantic model integration.
Provides structured error handling, serialization, and CLI exit code mapping.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- omnibase_core.enums.* (no dependencies on this module)
- omnibase_core.types.core_types (minimal types, no dependencies on this module)
- Standard library modules

Type-Only Imports (MUST use TYPE_CHECKING guard):
- omnibase_core.models.* (imports from types.constraints, which references this module)
- Any module that directly/indirectly imports from types.constraints

Import Chain:
1. types.core_types (minimal types, no external deps)
2. THIS MODULE (errors.model_onex_error) → imports types.core_types
3. models.common.model_schema_value → imports THIS MODULE
4. types.constraints → TYPE_CHECKING import of THIS MODULE
5. models.* → imports types.constraints

Breaking this chain (e.g., adding runtime import from models.*) will cause circular import!
"""

import re
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

# Safe runtime imports - no circular dependency risk
from omnibase_core.enums.enum_onex_status import EnumOnexStatus

# Import required enums from the same package
from omnibase_core.errors.error_codes import (
    EnumCLIExitCode,
    EnumOnexErrorCode,
    ModelCoreErrorCode,
    get_exit_code_for_status,
)

# Import extracted models
from omnibase_core.models.common.model_onex_error_data import _ModelOnexErrorData
from omnibase_core.types.core_types import BasicErrorContext

# Type-only imports - protected by TYPE_CHECKING to prevent circular imports
if TYPE_CHECKING:
    from omnibase_core.models.common.model_error_context import ModelErrorContext
    from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelOnexError(Exception):
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
        error_code: EnumOnexErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        correlation_id: UUID | None = None,
        timestamp: datetime | None = None,
        **context: Any,
    ) -> None:
        """
        Initialize an ONEX error with error code and status.

        Entry point pattern: If correlation_id is not provided, generates a new one.

        Args:
            message: Human-readable error message
            error_code: Canonical error code (optional)
            status: EnumOnexStatus for this error (default: ERROR)
            correlation_id: Correlation ID for tracking (auto-generated if not provided)
            timestamp: Optional timestamp (defaults to current time)
            **context: Additional context information
        """
        # Initialize the Exception
        super().__init__(message)

        # Handle correlation ID using UUID architecture pattern
        # ONEX principle: Use canonical UUID type throughout, not strings
        final_correlation_id: UUID = (
            correlation_id if correlation_id is not None else uuid4()
        )

        # Store simple context (no circular dependencies)
        self._simple_context = BasicErrorContext(
            file_path=(context.get("file_path") if isinstance(context, dict) else None),
            line_number=(
                context.get("line_number") if isinstance(context, dict) else None
            ),
            column_number=(
                context.get("column_number") if isinstance(context, dict) else None
            ),
            function_name=(
                context.get("function_name") if isinstance(context, dict) else None
            ),
            module_name=(
                context.get("module_name") if isinstance(context, dict) else None
            ),
            stack_trace=(
                context.get("stack_trace") if isinstance(context, dict) else None
            ),
            additional_context=(
                {
                    k: v
                    for k, v in context.items()
                    if k
                    not in {
                        "file_path",
                        "line_number",
                        "column_number",
                        "function_name",
                        "module_name",
                        "stack_trace",
                    }
                }
                if isinstance(context, dict)
                else {}
            ),
        )

        # Create the Pydantic model for structured data (using dict[str, Any]context, no circular deps)
        self.model = _ModelOnexErrorData(
            message=message,
            error_code=error_code,
            status=status,
            correlation_id=final_correlation_id,
            timestamp=timestamp or datetime.now(UTC),
            context=context if isinstance(context, dict) else {},
        )

    @classmethod
    def with_correlation_id(
        cls,
        message: str,
        correlation_id: UUID,
        error_code: EnumOnexErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        timestamp: datetime | None = None,
        **context: Any,
    ) -> "ModelOnexError":
        """
        Create an ONEX error with a specific correlation ID.

        Factory method for creating errors with predetermined correlation IDs,
        useful for continuing existing error contexts.

        Args:
            message: Human-readable error message
            correlation_id: Specific correlation ID to use
            error_code: Canonical error code (optional)
            status: EnumOnexStatus for this error (default: ERROR)
            timestamp: Optional timestamp (defaults to current time)
            **context: Additional context information

        Returns:
            ModelOnexError instance with the specified correlation ID
        """
        return cls(
            message=message,
            error_code=error_code,
            status=status,
            correlation_id=correlation_id,
            timestamp=timestamp,
            **context,
        )

    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        error_code: EnumOnexErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        **context: Any,
    ) -> "ModelOnexError":
        """
        Create an ONEX error from a standard Python exception.

        Factory method for wrapping existing exceptions with ONEX error
        features while preserving the original exception information.

        Args:
            exception: The original exception to wrap
            error_code: Canonical error code (optional)
            status: EnumOnexStatus for this error (default: ERROR)
            **context: Additional context information

        Returns:
            ModelOnexError instance wrapping the original exception
        """
        return cls(
            message=str(exception),
            error_code=error_code,
            status=status,
            **context,
        )

    @property
    def message(self) -> str:
        """Get the error message."""
        return self.model.message

    @property
    def error_code(self) -> EnumOnexErrorCode | str | None:
        """Get the error code."""
        return self.model.error_code

    @property
    def status(self) -> EnumOnexStatus:
        """Get the error status."""
        return self.model.status

    @property
    def correlation_id(self) -> UUID:
        """Get the correlation ID."""
        return self.model.correlation_id

    @property
    def timestamp(self) -> datetime | None:
        """Get the timestamp."""
        return self.model.timestamp

    @property
    def context(self) -> dict[str, Any]:
        """Get the context information."""
        # Return context as dict[str, Any]from BasicErrorContext (no circular dependencies)
        return self._simple_context.to_dict()

    def get_exit_code(self) -> int:
        """Get the appropriate CLI exit code for this error."""
        if isinstance(self.error_code, EnumOnexErrorCode):
            return self.error_code.get_exit_code()
        return get_exit_code_for_status(self.status)

    def __str__(self) -> str:
        """String representation including error code if available."""
        if self.error_code:
            # Use .value to get the string value for EnumOnexErrorCode enums
            error_code_str = (
                self.error_code.value
                if hasattr(self.error_code, "value")
                else str(self.error_code)
            )
            return f"[{error_code_str}] {self.message}"
        return self.message

    def model_dump(self) -> dict[str, Any]:
        """Convert error to dict[str, Any]ionary for serialization."""
        return self.model.model_dump()

    def model_dump_json(self) -> str:
        """Convert error to JSON string for logging/telemetry."""
        return self.model.model_dump_json()

    def to_json(self) -> str:
        """Convert error to JSON string for logging/telemetry (alias for model_dump_json)."""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelOnexError":
        """Create ModelOnexError from dict[str, Any]ionary."""
        model = _ModelOnexErrorData.model_validate(data)
        return cls(
            message=model.message,
            error_code=model.error_code,
            status=model.status,
            correlation_id=model.correlation_id,
            timestamp=model.timestamp,
            **model.context,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ModelOnexError":
        """Create ModelOnexError from JSON string."""
        model = _ModelOnexErrorData.model_validate_json(json_str)
        return cls(
            message=model.message,
            error_code=model.error_code,
            status=model.status,
            correlation_id=model.correlation_id,
            timestamp=model.timestamp,
            **model.context,
        )

    @classmethod
    def model_json_schema(cls) -> dict[str, Any]:
        """Get the JSON schema for ModelOnexError."""
        return _ModelOnexErrorData.model_json_schema()
