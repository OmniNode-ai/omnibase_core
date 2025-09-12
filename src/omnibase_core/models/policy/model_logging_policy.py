"""Pydantic model for ONEX Centralized Logging Policy.

This model provides type-safe access to logging policy configuration
and ensures policy validation and compliance checking.
"""

from typing import Literal

import semver
from pydantic import BaseModel, Field, field_validator


class ModelLoggingPattern(BaseModel):
    """Model for individual logging pattern configuration."""

    level: Literal["TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"]
    template: str
    fields: list[str]
    conditions: list[str] | None = None
    performance_tracking: bool | None = False
    include_metrics: bool | None = False
    performance_thresholds: dict[str, int] | None = None
    include_exc_info: bool | None = False
    integrate_with: list[str] | None = None
    alert_conditions: list[str] | None = None
    use_for: list[str] | None = None
    sanitization: bool | None = False


class ModelLoggingPhilosophy(BaseModel):
    """Model for logging philosophy configuration."""

    structured_logging: bool = True
    json_format: bool = True
    correlation_tracking: bool = True
    performance_awareness: bool = True
    security_first: bool = True
    observability_driven: bool = True


class ModelSubsystemOverride(BaseModel):
    """Model for subsystem-specific logging overrides."""

    function_entry: dict[str, str | bool] | None = None
    include_performance_metrics: bool | None = None
    alert_on_slow_functions: bool | None = None
    correlation_required: bool | None = None
    security_enhanced: bool | None = None
    audit_trail: bool | None = None
    batch_logging: bool | None = None
    reduce_verbosity: bool | None = None
    track_token_usage: bool | None = None
    track_model_calls: bool | None = None
    include_generation_metrics: bool | None = None
    track_requests: bool | None = None
    include_client_context: bool | None = None
    track_ai_operations: bool | None = None
    include_model_metadata: bool | None = None
    privacy_enhanced: bool | None = None
    include_user_context: bool | None = None


class ModelSecurityRules(BaseModel):
    """Model for security and privacy logging rules."""

    never_log: list[str]
    sanitize_patterns: list[str]
    pii_detection: dict[str, bool | list[str]]
    security_levels: dict[str, str]


class ModelPerformanceConfig(BaseModel):
    """Model for performance and resource management configuration."""

    max_log_entry_size: str
    max_daily_logs: str
    rotation_policy: str
    compression: bool
    async_logging: bool
    buffer_size: int
    flush_interval: str
    hot_path_detection: dict[str, bool | int]
    performance_monitoring: dict[str, bool | int]


class ModelIntegrations(BaseModel):
    """Model for external service integrations."""

    rag_service: dict[str, bool]
    knowledge_base: dict[str, bool]
    mcp_tools: dict[str, bool]
    monitoring: dict[str, bool]
    tracing: dict[str, bool]


class ModelAgentCoordination(BaseModel):
    """Model for agent coordination configuration."""

    share_context: bool
    avoid_duplicate_work: bool
    learn_from_other_agents: bool
    coordinate_logging_additions: bool
    context_sharing: dict[str, bool]


class ModelQualityGates(BaseModel):
    """Model for quality and compliance gates."""

    validate_log_format: bool
    check_security_compliance: bool
    verify_performance_impact: bool
    ensure_correlation_tracking: bool
    required_fields: list[str]
    optional_fields: list[str]


class ModelMaintenance(BaseModel):
    """Model for policy maintenance configuration."""

    review_schedule: str
    update_process: str
    version_control: bool
    stakeholders: list[str]


class ModelLoggingPolicy(BaseModel):
    """Complete model for ONEX Centralized Logging Policy."""

    version: str = Field(
        ...,
        description="Policy version following semantic versioning",
    )
    schema_version: str = Field(
        ...,
        description="Schema version following semantic versioning",
    )

    philosophy: ModelLoggingPhilosophy
    default_patterns: dict[str, ModelLoggingPattern]
    subsystem_overrides: dict[str, ModelSubsystemOverride]
    security: ModelSecurityRules
    performance: ModelPerformanceConfig
    integrations: ModelIntegrations
    agent_coordination: ModelAgentCoordination
    quality_gates: ModelQualityGates
    levels: dict[str, str]
    templates: dict[str, str]
    examples: dict[str, str]
    maintenance: ModelMaintenance

    @field_validator("version", "schema_version")
    @classmethod
    def validate_semver_versions(cls, v):
        """Validate that versions follow semantic versioning."""
        try:
            semver.VersionInfo.parse(v)
            return v
        except ValueError:
            msg = f"Version must be valid semver: {v}"
            raise ValueError(msg)

    @field_validator("default_patterns")
    @classmethod
    def validate_required_patterns(cls, v):
        """Ensure required logging patterns are present."""
        required_patterns = [
            "function_entry",
            "function_exit",
            "function_return",
            "error_handling",
            "operation_start",
            "operation_complete",
        ]

        missing_patterns = [
            pattern for pattern in required_patterns if pattern not in v
        ]
        if missing_patterns:
            msg = f"Missing required logging patterns: {missing_patterns}"
            raise ValueError(msg)

        return v

    def get_pattern_for_subsystem(
        self,
        pattern_name: str,
        subsystem: str,
    ) -> ModelLoggingPattern:
        """Get logging pattern with subsystem overrides applied."""
        base_pattern = self.default_patterns[pattern_name]

        if subsystem in self.subsystem_overrides:
            override = self.subsystem_overrides[subsystem]

            # Apply overrides - this is a simplified example
            if hasattr(override, "function_entry") and pattern_name == "function_entry":
                if override.function_entry and "level" in override.function_entry:
                    level_value = override.function_entry["level"]
                    # Type narrowing with proper Literal casting
                    if isinstance(level_value, str) and level_value in [
                        "TRACE",
                        "DEBUG",
                        "INFO",
                        "WARN",
                        "ERROR",
                        "FATAL",
                    ]:
                        # Use type: ignore or create new pattern to avoid Literal assignment
                        from typing import cast

                        from typing_extensions import Literal

                        LogLevel = Literal[
                            "TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"
                        ]
                        base_pattern.level = cast(LogLevel, level_value)

        return base_pattern

    def is_field_sensitive(self, field_name: str) -> bool:
        """Check if a field contains sensitive data that should not be logged."""
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in self.security.never_log)

    def should_sanitize_field(self, field_name: str) -> bool:
        """Check if a field should be sanitized before logging."""
        field_lower = field_name.lower()
        return any(
            pattern in field_lower for pattern in self.security.sanitize_patterns
        )

    def get_log_level_priority(self, level: str) -> int:
        """Get numeric priority for log level comparison."""
        level_priorities = {
            "TRACE": 0,
            "DEBUG": 1,
            "INFO": 2,
            "WARN": 3,
            "ERROR": 4,
            "FATAL": 5,
        }
        return level_priorities.get(level, 1)

    def is_compatible_with_version(self, other_version: str) -> bool:
        """Check if this policy version is compatible with another version."""
        try:
            current = semver.VersionInfo.parse(self.version)
            other = semver.VersionInfo.parse(other_version)

            # Compatible if major versions match (semantic versioning)
            return other.major == current.major
        except ValueError:
            return False


class ModelLoggingPolicyWrapper(BaseModel):
    """Wrapper model that matches the YAML structure."""

    logging_policy: ModelLoggingPolicy
