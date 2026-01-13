import contextlib
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    default_model_version,
    parse_semver_from_string,
)
from omnibase_core.models.services.model_custom_fields import ModelCustomFields
from omnibase_core.models.services.model_retry_strategy import ModelRetryStrategy


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

    # Note on from_attributes=True: Added for pytest-xdist parallel execution
    # compatibility. See CLAUDE.md "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    version: ModelSemVer = Field(
        default_factory=default_model_version,
        description="Schema version for input state (semantic version)",
    )
    input_field: str = Field(
        default=...,
        description="Required input field for event bus processing",
        min_length=1,
        max_length=1000,
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for tracking across operations",
    )
    event_id: UUID | None = Field(
        default=None,
        description="Unique event identifier",
    )
    integration: bool | None = Field(
        default=None, description="Integration mode flag for testing and validation"
    )
    custom: ModelCustomFields | None = Field(
        default=None, description="Custom metadata and configuration"
    )
    priority: str | None = Field(
        default="normal",
        description="Processing priority level",
        pattern="^(low|normal|high|critical)$",
    )
    timeout_seconds: int | None = Field(
        default=30, description="Processing timeout in seconds", ge=1, le=3600
    )
    retry_count: int | None = Field(
        default=3, description="Maximum retry attempts", ge=0, le=10
    )

    @field_validator("version", mode="before")
    @classmethod
    def parse_version(cls, v: Any) -> ModelSemVer:
        """Parse and validate semantic version."""
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            return parse_semver_from_string(v)
        if isinstance(v, dict):
            return ModelSemVer(**v)
        msg = "version must be a string, dict[str, Any], or ModelSemVer"
        raise ModelOnexError(error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg)

    @field_validator("input_field")
    @classmethod
    def validate_input_field(cls, v: str) -> str:
        """Validate input field content."""
        if not v or not v.strip():
            msg = "input_field cannot be empty or whitespace"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
            )
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
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
                )
        return v.strip()

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
        if self.is_high_priority():
            return min(base_timeout * 2, 3600)
        return base_timeout

    def get_retry_strategy(self) -> ModelRetryStrategy:
        """Get retry configuration strategy."""
        max_retries = self.retry_count or 3
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
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if self.correlation_id:
            metadata["correlation_id"] = str(self.correlation_id)
        if self.event_id:
            metadata["event_id"] = str(self.event_id)
        return metadata

    def validate_for_processing(self) -> list[str]:
        """Validate state is ready for processing."""
        issues = []
        if not self.input_field or not self.input_field.strip():
            issues.append("input_field is required and cannot be empty")
        if self.version.major == 0:
            issues.append("Pre-release versions (0.x.x) not recommended for production")
        if self.timeout_seconds and self.timeout_seconds < 5:
            issues.append("timeout_seconds should be at least 5 seconds")
        if self.retry_count and self.retry_count > 5 and (not self.is_high_priority()):
            issues.append(
                "High retry_count should be reserved for high priority operations"
            )
        return issues

    def is_valid_for_processing(self) -> bool:
        """Check if state is valid for processing."""
        return len(self.validate_for_processing()) == 0

    def apply_environment_overrides(
        self, env_prefix: str = "ONEX_EVENT_BUS_"
    ) -> "ModelEventBusInputState":
        """Apply environment variable overrides."""
        updates: dict[str, int | str] = {}
        if timeout := os.getenv(f"{env_prefix}TIMEOUT_SECONDS"):
            with contextlib.suppress(ValueError):
                updates["timeout_seconds"] = int(timeout)
        if priority := os.getenv(f"{env_prefix}PRIORITY"):
            if priority.lower() in {"low", "normal", "high", "critical"}:
                updates["priority"] = priority.lower()
        if retry_count := os.getenv(f"{env_prefix}RETRY_COUNT"):
            with contextlib.suppress(ValueError):
                updates["retry_count"] = int(retry_count)
        if updates:
            return self.model_copy(update=updates)
        return self

    def get_environment_mapping(
        self, env_prefix: str = "ONEX_EVENT_BUS_"
    ) -> dict[str, str]:
        """Get mapping of fields to environment variable names."""
        return {
            "timeout_seconds": f"{env_prefix}TIMEOUT_SECONDS",
            "priority": f"{env_prefix}PRIORITY",
            "retry_count": f"{env_prefix}RETRY_COUNT",
            "correlation_id": f"{env_prefix}CORRELATION_ID",
            "event_id": f"{env_prefix}EVENT_ID",
        }

    @classmethod
    def create_basic(
        cls, version: ModelSemVer | str, input_field: str
    ) -> "ModelEventBusInputState":
        """Create basic input state for simple operations."""
        parsed_version = (
            parse_semver_from_string(version) if isinstance(version, str) else version
        )
        return cls(version=parsed_version, input_field=input_field)

    @classmethod
    def create_with_tracking(
        cls,
        version: ModelSemVer | str,
        input_field: str,
        correlation_id: UUID,
        event_id: UUID | None = None,
    ) -> "ModelEventBusInputState":
        """Create input state with tracking information."""
        # Convert ModelSemVer to str if needed before parsing
        version_str = str(version) if isinstance(version, ModelSemVer) else version
        return cls(
            version=parse_semver_from_string(version_str),
            input_field=input_field,
            correlation_id=correlation_id,
            event_id=event_id or uuid4(),
        )

    @classmethod
    def create_high_priority(
        cls, version: ModelSemVer | str, input_field: str, timeout_seconds: int = 60
    ) -> "ModelEventBusInputState":
        """Create high priority input state with extended timeout."""
        # Convert ModelSemVer to str if needed before parsing
        version_str = str(version) if isinstance(version, ModelSemVer) else version
        return cls(
            version=parse_semver_from_string(version_str),
            input_field=input_field,
            priority="high",
            timeout_seconds=timeout_seconds,
            retry_count=5,
        )

    @classmethod
    def create_from_environment(
        cls, env_prefix: str = "ONEX_EVENT_BUS_"
    ) -> "ModelEventBusInputState":
        """Create input state from environment variables."""
        version_env = os.getenv(f"{env_prefix}VERSION", "1.0.0")
        input_field_env = os.getenv(f"{env_prefix}INPUT_FIELD", "")
        if not input_field_env:
            msg = f"Environment variable {env_prefix}INPUT_FIELD is required"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
            )
        config_data: dict[str, str | int | ModelSemVer | None] = {
            "version": parse_semver_from_string(version_env),
            "input_field": input_field_env,
        }
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
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Invalid timeout value '{timeout}' in {env_prefix}TIMEOUT_SECONDS: {e}",
                    details={"timeout": timeout, "env_prefix": env_prefix},
                    timestamp=datetime.now(UTC),
                    node_name="ModelEventBusInputState",
                ) from e
        if retry_count := os.getenv(f"{env_prefix}RETRY_COUNT"):
            try:
                config_data["retry_count"] = int(retry_count)
            except ValueError as e:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Invalid retry count value '{retry_count}' in {env_prefix}RETRY_COUNT: {e}",
                    details={"retry_count": retry_count, "env_prefix": env_prefix},
                    timestamp=datetime.now(UTC),
                    node_name="ModelEventBusInputState",
                ) from e
        version_raw = config_data["version"]
        input_field_raw = config_data["input_field"]
        if not isinstance(version_raw, ModelSemVer):
            msg = "version must be ModelSemVer"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
            )
        if not isinstance(input_field_raw, str):
            msg = "input_field must be str"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
            )
        version_value: ModelSemVer = version_raw
        input_field: str = input_field_raw
        correlation_id_raw = config_data.get("correlation_id")
        correlation_id_validated = (
            UUID(correlation_id_raw) if isinstance(correlation_id_raw, str) else None
        )
        event_id_raw = config_data.get("event_id")
        event_id_validated = (
            UUID(event_id_raw) if isinstance(event_id_raw, str) else None
        )
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
            version=version_value,
            input_field=input_field,
            correlation_id=correlation_id_validated,
            event_id=event_id_validated,
            priority=priority_validated,
            timeout_seconds=timeout_seconds_validated,
            retry_count=retry_count_validated,
        )
