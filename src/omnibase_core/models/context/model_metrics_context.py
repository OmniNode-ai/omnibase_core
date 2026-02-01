"""
Metrics context model for observability and distributed tracing.

This module provides ModelMetricsContext, a typed model for observability
metadata that replaces untyped dict[str, str] fields. It captures distributed
tracing information following the W3C Trace Context standard.

Thread Safety:
    ModelMetricsContext is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

See Also:
    - omnibase_core.models.context.model_session_context: Session context
    - omnibase_core.models.context.model_audit_metadata: Audit trail metadata
    - W3C Trace Context: https://www.w3.org/TR/trace-context/
"""

import re

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

__all__ = ["ModelMetricsContext"]

# W3C Trace Context format patterns
# trace_id: 32 lowercase hex characters (128 bits)
# span_id: 16 lowercase hex characters (64 bits)
_TRACE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_SPAN_ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")

# SemVer 2.0.0 pattern - duplicated from validator_common to avoid circular imports.
# The canonical definition is in omnibase_core.validation.validators.validator_common
# Pattern breakdown:
# - MAJOR.MINOR.PATCH: each a non-negative integer (no leading zeros except 0 itself)
# - PRERELEASE: optional, dot-separated identifiers (alphanumeric + hyphen)
# - BUILD: optional, dot-separated identifiers (alphanumeric + hyphen)
_SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def _validate_semver(value: str) -> str:
    """Validate SemVer 2.0.0 version string (local helper to avoid circular imports).

    This helper is designed for use in Pydantic field validators, so it raises
    ValueError directly (which Pydantic expects for validation failures).

    Args:
        value: Version string to validate

    Returns:
        The validated version string (unchanged if valid)

    Raises:
        ValueError: If the format is invalid or empty
    """
    if not value:
        # error-ok: Pydantic validator requires ValueError
        raise ValueError("Semantic version cannot be empty")

    if not _SEMVER_PATTERN.match(value):
        # error-ok: Pydantic validator requires ValueError
        raise ValueError(f"Invalid semantic version format: '{value}'")

    return value


class ModelMetricsContext(BaseModel):
    """Context model for observability and distributed tracing metadata.

    Supports W3C Trace Context standard for distributed tracing. All fields
    are optional as metrics context may be partially populated depending on
    the observability infrastructure and sampling decisions.

    Attributes:
        trace_id: Distributed trace ID in W3C Trace Context format (32 lowercase
            hex characters representing 128 bits). Identifies a distributed trace
            across multiple services.
        span_id: Current span ID (16 lowercase hex characters representing 64 bits).
            Identifies a single operation within a trace.
        parent_span_id: Parent span ID for establishing hierarchy in the trace tree.
            None for root spans.
        sampling_rate: Sampling rate between 0.0 and 1.0. Determines the probability
            that a trace is recorded. None indicates default sampling behavior.
        service_name: Name of the originating service (e.g., "onex-gateway",
            "compute-service"). Used for service map visualization.
        service_version: Version of the service in semver format (e.g., "1.2.3").
            Useful for correlating behavior changes with deployments.
        environment: Deployment environment identifier (e.g., "dev", "staging",
            "prod"). Enables filtering traces by environment.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from omnibase_core.models.context import ModelMetricsContext
        >>>
        >>> ctx = ModelMetricsContext(
        ...     trace_id="0af7651916cd43dd8448eb211c80319c",
        ...     span_id="b7ad6b7169203331",
        ...     sampling_rate=0.1,
        ...     service_name="onex-gateway",
        ...     service_version="1.2.3",
        ...     environment="prod",
        ... )
        >>> ctx.is_sampled()
        True
        >>> ctx.has_parent()
        False
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    trace_id: str | None = Field(
        default=None,
        description="Distributed trace ID (W3C Trace Context format: 32 hex chars)",
    )
    span_id: str | None = Field(
        default=None,
        description="Current span ID (16 hex chars)",
    )
    parent_span_id: str | None = Field(
        default=None,
        description="Parent span ID for hierarchy",
    )
    sampling_rate: float | None = Field(
        default=None,
        description="Sampling rate (0.0-1.0)",
    )
    service_name: str | None = Field(
        default=None,
        description="Originating service name",
    )
    service_version: str | None = Field(
        default=None,
        description="Service version (semver)",
    )
    environment: str | None = Field(
        default=None,
        description="Deployment environment (dev, staging, prod)",
    )

    @field_validator("trace_id", mode="before")
    @classmethod
    def validate_trace_id(cls, value: object) -> str | None:
        """Validate trace_id is in W3C Trace Context format (32 hex chars).

        Note: Uses `object` type hint because mode="before" validators receive
        raw input before Pydantic type coercion - input could be any type.

        Args:
            value: The raw input value to validate (any type, expected str or None).

        Returns:
            The validated trace ID string (lowercase), or None if input is None.

        Raises:
            ValueError: If the value is not a string or not a valid W3C trace ID format.
        """
        if value is None:
            return None
        if not isinstance(value, str):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(f"trace_id must be a string, got {type(value).__name__}")
        # Normalize to lowercase for comparison
        normalized = value.lower()
        if not _TRACE_ID_PATTERN.match(normalized):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"Invalid trace_id '{value}': must be 32 lowercase hex characters "
                "(W3C Trace Context format)"
            )
        return normalized

    @field_validator("span_id", "parent_span_id", mode="before")
    @classmethod
    def validate_span_format(cls, value: object, info: ValidationInfo) -> str | None:
        """Validate span_id or parent_span_id is 16 hex characters.

        This validator handles both span_id and parent_span_id fields, using
        the field_name from ValidationInfo to provide field-specific error messages.
        Both fields must conform to W3C Trace Context format (16 lowercase hex chars).

        Note: Uses `object` type hint because mode="before" validators receive
        raw input before Pydantic type coercion - input could be any type.

        Args:
            value: The raw input value to validate (any type, expected str or None).
            info: Pydantic validation info containing the field name (either
                'span_id' or 'parent_span_id').

        Returns:
            The validated span ID string (lowercase), or None if input is None.

        Raises:
            ValueError: If the value is not a string or not a valid span ID format.
        """
        if value is None:
            return None
        field_name = info.field_name
        if not isinstance(value, str):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"{field_name} must be a string, got {type(value).__name__}"
            )
        # Normalize to lowercase for comparison
        normalized = value.lower()
        if not _SPAN_ID_PATTERN.match(normalized):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"Invalid {field_name} '{value}': must be 16 lowercase hex characters"
            )
        return normalized

    @field_validator("sampling_rate", mode="before")
    @classmethod
    def validate_sampling_rate(cls, value: object) -> float | None:
        """Validate sampling_rate is between 0.0 and 1.0.

        Note: Uses `object` type hint because mode="before" validators receive
        raw input before Pydantic type coercion - input could be any type.

        Args:
            value: The raw input value to validate (any type, expected float/int or None).

        Returns:
            The validated sampling rate as float, or None if input is None.

        Raises:
            ValueError: If the value is not numeric or not between 0.0 and 1.0 inclusive.
        """
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int | float):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"sampling_rate must be a number, got {type(value).__name__}"
            )
        float_value = float(value)
        if not 0.0 <= float_value <= 1.0:
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"Invalid sampling_rate {value}: must be between 0.0 and 1.0 inclusive"
            )
        return float_value

    @field_validator("service_version", mode="before")
    @classmethod
    def validate_service_version_semver(cls, value: object) -> str | None:
        """Validate service_version follows SemVer 2.0.0 format.

        Validates that service_version conforms to Semantic Versioning 2.0.0
        specification (e.g., "1.0.0", "2.1.3-beta.1", "1.0.0+build.123").

        Note: Uses `object` type hint because mode="before" validators receive
        raw input before Pydantic type coercion - input could be any type.

        Args:
            value: The raw input value to validate (any type, expected str or None).

        Returns:
            The validated version string unchanged, or None if input is None.

        Raises:
            ValueError: If the value is not a string or doesn't match SemVer 2.0.0 format.
        """
        if value is None:
            return None
        if not isinstance(value, str):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"service_version must be a string, got {type(value).__name__}"
            )
        return _validate_semver(value)

    def is_sampled(self) -> bool:
        """Check if this context should be sampled for recording.

        Returns True if sampling_rate is None (default sampling) or if
        sampling_rate is greater than 0.

        Returns:
            True if the trace should be sampled, False otherwise.
        """
        if self.sampling_rate is None:
            return True
        return self.sampling_rate > 0.0

    def has_parent(self) -> bool:
        """Check if this span has a parent span.

        Returns:
            True if parent_span_id is set, False otherwise.
        """
        return self.parent_span_id is not None
