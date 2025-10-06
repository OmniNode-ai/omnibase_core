import contextlib
import os
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_custom_fields import ModelCustomFields
from omnibase_core.models.core.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)
from omnibase_core.models.service.model_custom_fields import ModelCustomFields
from omnibase_core.models.service.model_retry_strategy import ModelRetryStrategy


class ModelEventBusInputState(BaseModel):
    """
    Enterprise-grade input state for event bus nodes with comprehensive validation,
    business logic, and operational monitoring capabilities.

    Features:
    - Strong semantic versioning with validation
    - Flexible input field handling with business logic
    - Configuration integration and validation
    - Environment variable integration
    - Operational metadata and tracking
    - Factory methods for common use cases
    """

    version: ModelSemVer = Field(
        default=...,
        description="Schema version for input state (semantic version)",
    )

    input_field: str = Field(
        default=...,
        description="Required input field for event bus processing",
        min_length=1,
        max_length=1000,
    )

    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for tracking across operations",
        max_length=100,
    )

    event_id: str | None = Field(
        default=None,
        description="Unique event identifier",
        max_length=100,
    )

    integration: bool | None = Field(
        default=None,
        description="Integration mode flag for testing and validation",
    )

    custom: ModelCustomFields | None = Field(
        default=None,
        description="Custom metadata and configuration",
    )

    priority: str | None = Field(
        default="normal",
        description="Processing priority level",
        pattern=r"^(low|normal|high|critical)$",
    )

    timeout_seconds: int | None = Field(
        default=30,
        description="Processing timeout in seconds",
        ge=1,
        le=3600,
    )

    retry_count: int | None = Field(
        default=3,
        description="Maximum retry attempts",
        ge=0,
        le=10,
    )

    @field_validator("version", mode="before")
    @classmethod
    def parse_version(cls, v: Any) -> Any:
        """Parse and validate semantic version."""
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            return parse_semver_from_string(v)
        if isinstance(v, dict):
            return ModelSemVer(**v)
        msg = "version must be a string, dict[str, Any], or ModelSemVer"
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    @field_validator("input_field")
    @classmethod
    def validate_input_field(cls, v: str) -> str:
        """Validate input field content."""
        if not v or not v.strip():
            msg = "input_field cannot be empty or whitespace"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        # Remove any potential script injection patterns
        dangerous_patterns = [
            "<script",
            "javascript:",
            "vbscript:",
            "onload=",
            "onerror=",
        ]
        v_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in v_lower:
                msg = f"input_field contains potentially dangerous pattern: {pattern}"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

        return v.strip()

    @field_validator("correlation_id")
    @classmethod
    def validate_correlation_id(cls, v: str | None) -> str | None:
        """Validate correlation ID format."""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Basic format validation (alphanumeric, hyphens, underscores)
        import re

        if not re.match(r"^[a-zA-Z0-9\-_]+$", v):
            msg = "correlation_id must contain only alphanumeric characters, hyphens, and underscores"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return v

    # === Business Logic Methods ===

    def get_processing_priority(self) -> int:
        """Get numeric priority for processing queue ordering."""
        priority_map = {"low": 1, "normal": 5, "high": 8, "critical": 10}
        return priority_map.get(self.priority or "normal", 5)

    def is_high_priority(self) -> bool:
        """Check if this is a high priority operation."""
        return self.get_processing_priority() >= 8

    def get_effective_timeout(self) -> int:
        """Get effective timeout with priority adjustments."""
        base_timeout = self.timeout_seconds or 30

        # High priority gets extended timeout
        if self.is_high_priority():
            return min(base_timeout * 2, 3600)

        return base_timeout

    def get_retry_strategy(self) -> ModelRetryStrategy:
        """Get retry configuration strategy."""
        max_retries = self.retry_count or 3

        # High priority operations get more retries
        if self.is_high_priority():
            max_retries = min(max_retries + 2, 10)

        return ModelRetryStrategy(
            max_retries=max_retries,
            backoff_multiplier=2.0 if self.is_high_priority() else 1.5,
            max_backoff=60 if self.is_high_priority() else 30,
            retry_on_timeout=True,
        )

    def get_tracking_metadata(self) -> dict[str, str]:
        """Get metadata for operation tracking."""
        metadata = {
            "version": str(self.version),
            "priority": self.priority or "normal",
            "timestamp": datetime.now().isoformat(),
        }

        if self.correlation_id:
            metadata["correlation_id"] = self.correlation_id

        if self.event_id:
            metadata["event_id"] = self.event_id

        return metadata

    def validate_for_processing(self) -> list[str]:
        """Validate state is ready for processing."""
        issues = []

        # Check required fields
        if not self.input_field or not self.input_field.strip():
            issues.append("input_field is required and cannot be empty")

        # Check version compatibility
        if self.version.major == 0:
            issues.append("Pre-release versions (0.x.x) not recommended for production")

        # Check configuration consistency
        if self.timeout_seconds and self.timeout_seconds < 5:
            issues.append("timeout_seconds should be at least 5 seconds")

        if self.retry_count and self.retry_count > 5 and not self.is_high_priority():
            issues.append(
                "High retry_count should be reserved for high priority operations",
            )

        return issues

    def is_valid_for_processing(self) -> bool:
        """Check if state is valid for processing."""
        return len(self.validate_for_processing()) == 0

    # === Configuration Integration ===

    def apply_environment_overrides(
        self,
        env_prefix: str = "ONEX_EVENT_BUS_",
    ) -> "ModelEventBusInputState":
        """Apply environment variable overrides."""
        updates: dict[str, int | str] = {}

        # Check for environment variable overrides
        if timeout := os.getenv(f"{env_prefix}TIMEOUT_SECONDS"):
            with contextlib.suppress(ValueError):
                updates["timeout_seconds"] = int(timeout)

        if priority := os.getenv(f"{env_prefix}PRIORITY"):
            if priority.lower() in ["low", "normal", "high", "critical"]:
                updates["priority"] = priority.lower()

        if retry_count := os.getenv(f"{env_prefix}RETRY_COUNT"):
            with contextlib.suppress(ValueError):
                updates["retry_count"] = int(retry_count)

        if updates:
            return self.model_copy(update=updates)

        return self

    def get_environment_mapping(
        self,
        env_prefix: str = "ONEX_EVENT_BUS_",
    ) -> dict[str, str]:
        """Get mapping of fields to environment variable names."""
        return {
            "timeout_seconds": f"{env_prefix}TIMEOUT_SECONDS",
            "priority": f"{env_prefix}PRIORITY",
            "retry_count": f"{env_prefix}RETRY_COUNT",
            "correlation_id": f"{env_prefix}CORRELATION_ID",
            "event_id": f"{env_prefix}EVENT_ID",
        }

    # === Factory Methods ===

    @classmethod
    def create_basic(cls, version: str, input_field: str) -> "ModelEventBusInputState":
        """Create basic input state for simple operations."""
        return cls(version=parse_semver_from_string(version), input_field=input_field)

    @classmethod
    def create_with_tracking(
        cls,
        version: str,
        input_field: str,
        correlation_id: str,
        event_id: str | None = None,
    ) -> "ModelEventBusInputState":
        """Create input state with tracking information."""
        return cls(
            version=parse_semver_from_string(version),
            input_field=input_field,
            correlation_id=correlation_id,
            event_id=event_id or f"evt_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )

    @classmethod
    def create_high_priority(
        cls,
        version: str,
        input_field: str,
        timeout_seconds: int = 60,
    ) -> "ModelEventBusInputState":
        """Create high priority input state with extended timeout."""
        return cls(
            version=parse_semver_from_string(version),
            input_field=input_field,
            priority="high",
            timeout_seconds=timeout_seconds,
            retry_count=5,
        )

    @classmethod
    def create_from_environment(
        cls,
        env_prefix: str = "ONEX_EVENT_BUS_",
    ) -> "ModelEventBusInputState":
        """Create input state from environment variables."""
        version = os.getenv(f"{env_prefix}VERSION", "1.0.0")
        input_field = os.getenv(f"{env_prefix}INPUT_FIELD", "")

        if not input_field:
            msg = f"Environment variable {env_prefix}INPUT_FIELD is required"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        config_data: dict[str, str | int | ModelSemVer | None] = {
            "version": parse_semver_from_string(version),
            "input_field": input_field,
        }

        # Optional environment variables
        if correlation_id := os.getenv(f"{env_prefix}CORRELATION_ID"):
            config_data["correlation_id"] = correlation_id

        if event_id := os.getenv(f"{env_prefix}EVENT_ID"):
            config_data["event_id"] = event_id

        if priority := os.getenv(f"{env_prefix}PRIORITY"):
            config_data["priority"] = priority

        if timeout := os.getenv(f"{env_prefix}TIMEOUT_SECONDS"):
            try:
                config_data["timeout_seconds"] = int(timeout)
            except ValueError as e:
                raise ModelOnexError(
                    error_code="INVALID_INPUT",
                    message=f"Invalid timeout value '{timeout}' in {env_prefix}TIMEOUT_SECONDS: {e}",
                    details={"timeout": timeout, "env_prefix": env_prefix},
                    timestamp=datetime.now(),
                    node_name="ModelEventBusInputState",
                ) from e

        if retry_count := os.getenv(f"{env_prefix}RETRY_COUNT"):
            try:
                config_data["retry_count"] = int(retry_count)
            except ValueError as e:
                raise ModelOnexError(
                    error_code="INVALID_INPUT",
                    message=f"Invalid retry count value '{retry_count}' in {env_prefix}RETRY_COUNT: {e}",
                    details={"retry_count": retry_count, "env_prefix": env_prefix},
                    timestamp=datetime.now(),
                    node_name="ModelEventBusInputState",
                ) from e

        # Create instance with proper type handling
        version = config_data["version"]
        if not isinstance(version, ModelSemVer):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="version must be ModelSemVer",
            )

        input_field = config_data["input_field"]
        if not isinstance(input_field, str):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="input_field must be str",
            )

        # Extract and validate fields with proper type checking
        correlation_id_raw = config_data.get("correlation_id")
        correlation_id_validated = (
            correlation_id_raw if isinstance(correlation_id_raw, str) else None
        )

        event_id_raw = config_data.get("event_id")
        event_id_validated = event_id_raw if isinstance(event_id_raw, str) else None

        priority_raw = config_data.get("priority")
        priority_validated = priority_raw if isinstance(priority_raw, str) else None

        timeout_seconds_raw = config_data.get("timeout_seconds")
        timeout_seconds_validated = (
            timeout_seconds_raw if isinstance(timeout_seconds_raw, int) else None
        )

        retry_count_raw = config_data.get("retry_count")
        retry_count_validated = (
            retry_count_raw if isinstance(retry_count_raw, int) else None
        )

        return cls(
            version=version,
            input_field=input_field,
            correlation_id=correlation_id_validated,
            event_id=event_id_validated,
            priority=priority_validated,
            timeout_seconds=timeout_seconds_validated,
            retry_count=retry_count_validated,
        )
