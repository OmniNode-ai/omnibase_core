"""Pydantic model for ONEX Centralized Logging Policy.

This model provides type-safe access to logging policy configuration
and ensures policy validation and compliance checking.
"""

from typing import Dict, List, Literal, Optional, Union

import semver
from pydantic import BaseModel, Field, validator


class ModelLoggingPattern(BaseModel):
    """Model for individual logging pattern configuration."""

    level: Literal["TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"]
    template: str
    fields: List[str]
    conditions: Optional[List[str]] = None
    performance_tracking: Optional[bool] = False
    include_metrics: Optional[bool] = False
    performance_thresholds: Optional[Dict[str, int]] = None
    include_exc_info: Optional[bool] = False
    integrate_with: Optional[List[str]] = None
    alert_conditions: Optional[List[str]] = None
    use_for: Optional[List[str]] = None
    sanitization: Optional[bool] = False


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

    function_entry: Optional[Dict[str, Union[str, bool]]] = None
    include_performance_metrics: Optional[bool] = None
    alert_on_slow_functions: Optional[bool] = None
    correlation_required: Optional[bool] = None
    security_enhanced: Optional[bool] = None
    audit_trail: Optional[bool] = None
    batch_logging: Optional[bool] = None
    reduce_verbosity: Optional[bool] = None
    track_token_usage: Optional[bool] = None
    track_model_calls: Optional[bool] = None
    include_generation_metrics: Optional[bool] = None
    track_requests: Optional[bool] = None
    include_client_context: Optional[bool] = None
    track_ai_operations: Optional[bool] = None
    include_model_metadata: Optional[bool] = None
    privacy_enhanced: Optional[bool] = None
    include_user_context: Optional[bool] = None


class ModelSecurityRules(BaseModel):
    """Model for security and privacy logging rules."""

    never_log: List[str]
    sanitize_patterns: List[str]
    pii_detection: Dict[str, Union[bool, List[str]]]
    security_levels: Dict[str, str]


class ModelPerformanceConfig(BaseModel):
    """Model for performance and resource management configuration."""

    max_log_entry_size: str
    max_daily_logs: str
    rotation_policy: str
    compression: bool
    async_logging: bool
    buffer_size: int
    flush_interval: str
    hot_path_detection: Dict[str, Union[bool, int]]
    performance_monitoring: Dict[str, Union[bool, int]]


class ModelIntegrations(BaseModel):
    """Model for external service integrations."""

    rag_service: Dict[str, bool]
    knowledge_base: Dict[str, bool]
    mcp_tools: Dict[str, bool]
    monitoring: Dict[str, bool]
    tracing: Dict[str, bool]


class ModelAgentCoordination(BaseModel):
    """Model for agent coordination configuration."""

    share_context: bool
    avoid_duplicate_work: bool
    learn_from_other_agents: bool
    coordinate_logging_additions: bool
    context_sharing: Dict[str, bool]


class ModelQualityGates(BaseModel):
    """Model for quality and compliance gates."""

    validate_log_format: bool
    check_security_compliance: bool
    verify_performance_impact: bool
    ensure_correlation_tracking: bool
    required_fields: List[str]
    optional_fields: List[str]


class ModelMaintenance(BaseModel):
    """Model for policy maintenance configuration."""

    review_schedule: str
    update_process: str
    version_control: bool
    backward_compatibility: str
    stakeholders: List[str]

    @validator("backward_compatibility")
    def validate_semver(cls, v):
        """Validate that backward_compatibility follows semantic versioning."""
        try:
            semver.VersionInfo.parse(v)
            return v
        except ValueError:
            raise ValueError(f"backward_compatibility must be valid semver: {v}")


class ModelLoggingPolicy(BaseModel):
    """Complete model for ONEX Centralized Logging Policy."""

    version: str = Field(
        ..., description="Policy version following semantic versioning"
    )
    schema_version: str = Field(
        ..., description="Schema version following semantic versioning"
    )

    philosophy: ModelLoggingPhilosophy
    default_patterns: Dict[str, ModelLoggingPattern]
    subsystem_overrides: Dict[str, ModelSubsystemOverride]
    security: ModelSecurityRules
    performance: ModelPerformanceConfig
    integrations: ModelIntegrations
    agent_coordination: ModelAgentCoordination
    quality_gates: ModelQualityGates
    levels: Dict[str, str]
    templates: Dict[str, str]
    examples: Dict[str, str]
    maintenance: ModelMaintenance

    @validator("version", "schema_version")
    def validate_semver_versions(cls, v):
        """Validate that versions follow semantic versioning."""
        try:
            semver.VersionInfo.parse(v)
            return v
        except ValueError:
            raise ValueError(f"Version must be valid semver: {v}")

    @validator("default_patterns")
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
            raise ValueError(f"Missing required logging patterns: {missing_patterns}")

        return v

    def get_pattern_for_subsystem(
        self, pattern_name: str, subsystem: str
    ) -> ModelLoggingPattern:
        """Get logging pattern with subsystem overrides applied."""
        base_pattern = self.default_patterns[pattern_name]

        if subsystem in self.subsystem_overrides:
            override = self.subsystem_overrides[subsystem]

            # Apply overrides - this is a simplified example
            if hasattr(override, "function_entry") and pattern_name == "function_entry":
                if override.function_entry and "level" in override.function_entry:
                    base_pattern.level = override.function_entry["level"]

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
            backward_compat = semver.VersionInfo.parse(
                self.maintenance.backward_compatibility
            )

            # Compatible if other version is within backward compatibility range
            return other >= backward_compat and other.major == current.major
        except ValueError:
            return False


class ModelLoggingPolicyWrapper(BaseModel):
    """Wrapper model that matches the YAML structure."""

    logging_policy: ModelLoggingPolicy
