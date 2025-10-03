"""
Fail Fast Mixin for ONEX Tool Nodes.

Provides consistent error handling patterns and fail-fast behavior.
Ensures tools crash early with clear error messages rather than continuing in invalid states.
"""

import sys
import traceback
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import TypeVar

from omnibase_core.core.errors.core_errors import CoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.exceptions import OnexError
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.core.model_onex_error import ModelOnexError

# Type variable for return types
T = TypeVar("T")


class FailFastError(Exception):
    """Base exception for fail-fast scenarios."""

    def __init__(
        self,
        message: str,
        error_code: str = "FAIL_FAST",
        details: dict | None = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class ValidationFailedError(FailFastError):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: str | int | float | None = None,
    ):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(message, "VALIDATION_FAILED", details)


class DependencyFailedError(FailFastError):
    """Raised when a required dependency is not available."""

    def __init__(self, message: str, dependency: str):
        super().__init__(message, "DEPENDENCY_FAILED", {"dependency": dependency})


class ContractViolationError(FailFastError):
    """Raised when contract requirements are violated."""

    def __init__(self, message: str, contract_field: str):
        super().__init__(
            message,
            "CONTRACT_VIOLATION",
            {"contract_field": contract_field},
        )


class MixinFailFast:
    """
    Mixin that provides fail-fast error handling for tool nodes.

    Features:
    - Consistent error reporting
    - Automatic crash on critical errors
    - Validation helpers
    - Contract enforcement
    - Dependency checking

    Usage:
        class MyTool(MixinFailFast, ProtocolReducer):
            def process(self, input_state):
                # Validate required fields
                self.validate_required(input_state.config, "config")
                self.validate_not_empty(input_state.data, "data")

                # Check dependencies
                self.require_dependency("database", self.check_db_connection)

                # Use fail_fast decorator on critical methods
                @self.fail_fast
                def critical_operation():
                    # This will crash the tool if it raises
                    pass
    """

    def __init__(self, **kwargs):
        """Initialize the fail fast mixin."""
        super().__init__(**kwargs)

        emit_log_event(
            LogLevel.DEBUG,
            "🏗️ MIXIN_INIT: Initializing MixinFailFast",
            {"mixin_class": self.__class__.__name__},
        )

    def fail_fast(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator that makes a function fail fast on any exception.

        Usage:
            @self.fail_fast
            def critical_method(self):
                # Any exception here will crash the process
                pass
        """

        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except FailFastError:
                # Re-raise our own fail fast errors
                raise
            except Exception as e:
                # Convert other exceptions to fail fast
                self._handle_critical_error(
                    f"Critical error in {func.__name__}: {e!s}",
                    error_type=type(e).__name__,
                    function=func.__name__,
                    traceback=traceback.format_exc(),
                )

        return wrapper

    def validate_required(self, value: T | None, field_name: str) -> T:
        """
        Validate that a required field is not None.

        Args:
            value: Value to check
            field_name: Name of the field for error reporting

        Returns:
            The value if not None

        Raises:
            ValidationFailedError if value is None
        """
        if value is None:
            msg = f"Required field '{field_name}' is missing"
            raise OnexError(
                msg,
                error_code=CoreErrorCode.VALIDATION_FAILED,
            )
        return value

    def validate_not_empty(
        self,
        value: str | list | dict,
        field_name: str,
    ) -> str | list | dict:
        """
        Validate that a field is not empty.

        Args:
            value: Value to check
            field_name: Name of the field for error reporting

        Returns:
            The value if not empty

        Raises:
            ValidationFailedError if value is empty
        """
        if not value:
            msg = f"Field '{field_name}' cannot be empty"
            raise OnexError(
                msg,
                error_code=CoreErrorCode.VALIDATION_FAILED,
            )
        return value

    def validate_type(
        self,
        value: object,
        expected_type: type,
        field_name: str,
    ) -> object:
        """
        Validate that a field has the expected type using duck typing.

        Args:
            value: Value to check
            expected_type: Expected type
            field_name: Name of the field for error reporting

        Returns:
            The value if type matches

        Raises:
            ValidationFailedError if type doesn't match
        """
        # Use duck typing by checking if value has expected type's attributes/methods
        actual_type = type(value)
        if actual_type != expected_type:
            # Check if the value has the essential characteristics of the expected type
            if hasattr(expected_type, "__bases__"):
                # For class types, check if value has similar interface
                expected_methods = [
                    attr for attr in dir(expected_type) if not attr.startswith("_")
                ]
                value_methods = [
                    attr for attr in dir(value) if not attr.startswith("_")
                ]

                # If value doesn't have key methods/attributes, it's not compatible
                key_missing = []
                for method in expected_methods:
                    if method not in value_methods and hasattr(expected_type, method):
                        key_missing.append(method)

                # Allow some missing methods for duck typing compatibility
                if (
                    len(key_missing) > len(expected_methods) * 0.5
                ):  # More than 50% missing
                    msg = f"Field '{field_name}' must be compatible with type {expected_type.__name__}, got {actual_type.__name__}"
                    raise OnexError(
                        msg,
                        error_code=CoreErrorCode.VALIDATION_FAILED,
                    )
            # For basic types, check essential characteristics
            elif expected_type == str and not hasattr(value, "split"):
                msg = f"Field '{field_name}' must be string-like, got {actual_type.__name__}"
                raise OnexError(
                    msg,
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                )
            elif expected_type == int and not hasattr(value, "__add__"):
                msg = (
                    f"Field '{field_name}' must be numeric, got {actual_type.__name__}"
                )
                raise OnexError(
                    msg,
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                )
            elif expected_type == list and not hasattr(value, "append"):
                msg = f"Field '{field_name}' must be list-like, got {actual_type.__name__}"
                raise OnexError(
                    msg,
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                )
            elif expected_type == dict and not hasattr(value, "keys"):
                msg = f"Field '{field_name}' must be dict-like, got {actual_type.__name__}"
                raise OnexError(
                    msg,
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                )

        return value

    def validate_enum(self, value: str, allowed_values: list, field_name: str) -> str:
        """
        Validate that a field value is in allowed list.

        Args:
            value: Value to check
            allowed_values: List of allowed values
            field_name: Name of the field for error reporting

        Returns:
            The value if allowed

        Raises:
            ValidationFailedError if value not allowed
        """
        if value not in allowed_values:
            msg = f"Field '{field_name}' must be one of {allowed_values}, got '{value}'"
            raise OnexError(
                msg,
                error_code=CoreErrorCode.VALIDATION_FAILED,
            )
        return value

    def require_dependency(
        self,
        dependency_name: str,
        check_func: Callable[[], bool],
    ) -> None:
        """
        Require that a dependency is available.

        Args:
            dependency_name: Name of the dependency
            check_func: Function that returns True if dependency is available

        Raises:
            DependencyFailedError if dependency check fails
        """
        try:
            if not check_func():
                msg = f"Required dependency '{dependency_name}' is not available"
                raise OnexError(
                    msg,
                    error_code=CoreErrorCode.DEPENDENCY_FAILED,
                )
        except Exception as e:
            msg = f"Failed to check dependency '{dependency_name}': {e!s}"
            raise OnexError(
                msg,
                error_code=CoreErrorCode.DEPENDENCY_FAILED,
            )

    def enforce_contract(
        self,
        condition: bool,
        message: str,
        contract_field: str,
    ) -> None:
        """
        Enforce a contract requirement.

        Args:
            condition: Condition that must be True
            message: Error message if condition is False
            contract_field: Contract field being enforced

        Raises:
            ContractViolationError if condition is False
        """
        if not condition:
            raise OnexError(
                code=CoreErrorCode.CONTRACT_VIOLATION,
                message=message,
            )

    def _handle_critical_error(self, message: str, **details) -> None:
        """
        Handle a critical error by logging and exiting.

        Args:
            message: Error message
            **details: Additional error details to log
        """
        # Log the error
        emit_log_event(
            LogLevel.ERROR,
            f"💥 FAIL_FAST: {message}",
            {"node_class": self.__class__.__name__, **details},
        )

        # Create error model for structured output
        ModelOnexError(
            error_code="FAIL_FAST",
            message=message,
            details=details,
            timestamp=datetime.utcnow(),
            node_name=getattr(self, "node_name", self.__class__.__name__),
            severity="CRITICAL",
        )

        # Print to stderr for visibility

        if details:
            for _key, _value in details.items():
                pass

        # Exit with error code
        sys.exit(1)

    def handle_error(self, error: Exception, context: str = "unknown") -> None:
        """
        Handle an error with appropriate action based on type.

        Args:
            error: The exception to handle
            context: Context where the error occurred
        """
        # Fail fast errors should crash immediately - use duck typing
        if hasattr(error, "error_code") and hasattr(error, "details"):
            self._handle_critical_error(
                str(error),
                error_code=error.error_code,
                context=context,
                **error.details,
            )

        # Other errors might be recoverable - let caller decide
        else:
            emit_log_event(
                LogLevel.ERROR,
                f"Error in {context}: {error!s}",
                {
                    "node_class": self.__class__.__name__,
                    "error_type": type(error).__name__,
                    "context": context,
                },
            )
