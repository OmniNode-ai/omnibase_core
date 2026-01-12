"""
Configuration Management Subcontract Model.


Dedicated subcontract model for configuration management functionality providing:
- Configuration source specification with priority handling
- Validation rules and constraints for configuration data
- Environment-specific configuration management
- Runtime configuration updates and monitoring
- Sensitive data handling and security

This model is composed into node contracts that require configuration management functionality,
providing clean separation between node logic and configuration behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pathlib import Path
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_environment import EnumEnvironment
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Import individual configuration model components
from .model_configuration_source import ModelConfigurationSource
from .model_configuration_validation import ModelConfigurationValidation


class ModelConfigurationSubcontract(BaseModel):
    """
    Configuration management subcontract for infrastructure nodes.

    Provides standardized configuration loading, validation, merging,
    and runtime reconfiguration capabilities for ONEX infrastructure
    components such as databases, message queues, and external services.

    This subcontract enables infrastructure nodes to:
    - Load configuration from multiple sources with priority
    - Validate configuration against schemas and constraints
    - Handle environment-specific configuration variants
    - Support runtime configuration updates with validation
    - Manage sensitive configuration data securely
    - Monitor configuration sources for changes

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )

    # ONEX: Universal correlation ID for tracing
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique correlation ID for configuration tracking",
    )

    # Configuration identification
    config_name: str = Field(
        default=...,
        description="Unique identifier for this configuration set",
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        min_length=1,
        max_length=128,
    )

    config_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the configuration schema (MUST be provided in YAML contract)",
    )

    # Configuration sources
    configuration_sources: list[ModelConfigurationSource] = Field(
        default_factory=list,
        description="Ordered list[Any]of configuration sources by priority",
    )

    default_source_type: str = Field(
        default="file",
        description="Default configuration source type",
        pattern=r"^[a-z_]+$",
    )

    # Environment integration
    target_environment: EnumEnvironment = Field(
        default=EnumEnvironment.DEVELOPMENT,
        description="Target deployment environment",
    )

    environment_variable_prefix: str | None = Field(
        default=None,
        description="Prefix for environment variable configuration keys",
        pattern=r"^[A-Z][A-Z0-9_]*$",
    )

    inherit_environment: bool = Field(
        default=True,
        description="Whether to inherit configuration from environment variables",
    )

    # Validation and constraints
    validation_rules: ModelConfigurationValidation = Field(
        default_factory=lambda: ModelConfigurationValidation(
            version=ModelSemVer(major=1, minor=0, patch=0)
        ),
        description="Configuration validation rules and constraints",
    )

    strict_validation: bool = Field(
        default=True,
        description="Whether to enforce strict configuration validation",
    )

    fail_on_missing_required: bool = Field(
        default=True,
        description="Whether to fail when required configuration is missing",
    )

    # Runtime behavior
    allow_runtime_updates: bool = Field(
        default=False,
        description="Whether to allow configuration updates at runtime",
    )

    auto_reload_on_change: bool = Field(
        default=False,
        description="Whether to automatically reload configuration when sources change",
    )

    reload_debounce_seconds: float = Field(
        default=5.0,
        description="Debounce time for configuration reload in seconds",
        ge=1.0,  # Minimum 1 second to prevent reload thrashing
        le=300.0,
    )

    # Security and sensitive data
    encrypt_sensitive_values: bool = Field(
        default=True,
        description="Whether to encrypt sensitive configuration values",
    )

    mask_sensitive_in_logs: bool = Field(
        default=True,
        description="Whether to mask sensitive values in log output",
    )

    # Backup and recovery
    backup_configuration: bool = Field(
        default=True,
        description="Whether to create backups of configuration changes",
    )

    max_backup_versions: int = Field(
        default=10,
        description="Maximum number of configuration backup versions to keep",
        ge=1,
        le=100,
    )

    backup_directory: Path | None = Field(
        default=None,
        description="Directory for configuration backups",
    )

    # Integration settings
    integration_timeout_seconds: float = Field(
        default=30.0,
        description="Timeout for configuration integration operations",
        gt=0.0,
        le=300.0,
    )

    health_check_configuration: bool = Field(
        default=True,
        description="Whether to include configuration status in health checks",
    )

    # Logging and monitoring
    log_configuration_changes: bool = Field(
        default=True,
        description="Whether to log configuration changes",
    )

    configuration_log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Log level for configuration-related messages",
    )

    emit_configuration_events: bool = Field(
        default=False,
        description="Whether to emit events for configuration changes",
    )

    @model_validator(mode="after")
    def validate_configuration_sources(self) -> "ModelConfigurationSubcontract":
        """Validate configuration sources have unique priorities when required."""
        if len(self.configuration_sources) <= 1:
            return self

        # Check for duplicate priorities among required sources
        required_priorities = [
            src.priority for src in self.configuration_sources if src.required
        ]
        if len(required_priorities) != len(set(required_priorities)):
            raise ModelOnexError(
                message="Required configuration sources cannot have duplicate priorities",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        return self

    @model_validator(mode="after")
    def validate_validation_rules(self) -> "ModelConfigurationSubcontract":
        """Validate that required and optional keys don't overlap."""
        required_set = set(self.validation_rules.required_keys)
        optional_set = set(self.validation_rules.optional_keys)

        if required_set & optional_set:
            overlapping = required_set & optional_set
            msg = f"Keys cannot be both required and optional: {overlapping}"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        return self

    def get_effective_environment_prefix(self) -> str | None:
        """
        Get the effective environment variable prefix.

        Returns:
            Environment variable prefix or None if not configured
        """
        if self.environment_variable_prefix:
            return self.environment_variable_prefix
        if self.inherit_environment:
            # Generate default prefix from config name
            return f"{self.config_name.upper().replace('-', '_')}_"
        return None

    def is_key_sensitive(self, key: str) -> bool:
        """
        Check if a configuration key contains sensitive data.

        Args:
            key: Configuration key to check

        Returns:
            True if key is marked as sensitive
        """
        return key in self.validation_rules.sensitive_keys

    def get_required_keys_for_environment(
        self,
        environment: EnumEnvironment | None = None,
    ) -> list[str]:
        """
        Get required configuration keys for a specific environment.

        Args:
            environment: Target environment (uses target_environment if not specified)

        Returns:
            List of required configuration keys
        """
        env = environment or self.target_environment
        base_keys = self.validation_rules.required_keys.copy()

        # Add environment-specific required keys
        env_rules = next(
            (
                rules
                for rules in self.validation_rules.environment_specific
                if rules.environment == env
            ),
            None,
        )

        env_required = []
        if env_rules:
            env_required = [
                rule.config_key
                for rule in env_rules.validation_rules
                if rule.validation_rule == "required"
            ]

        return list(set(base_keys + env_required))

    def should_reload_on_change(self, source_type: str) -> bool:
        """
        Check if configuration should be reloaded for a given source type change.

        Args:
            source_type: Type of configuration source that changed

        Returns:
            True if configuration should be reloaded
        """
        if not self.auto_reload_on_change:
            return False

        # Check if any source of this type has watch_for_changes enabled
        for source in self.configuration_sources:
            if source.source_type == source_type and source.watch_for_changes:
                return True

        return False

    def get_backup_path(self, version: int) -> Path | None:
        """
        Get the backup path for a specific configuration version.

        Args:
            version: Backup version number

        Returns:
            Path to backup file or None if backup directory not configured
        """
        if not self.backup_directory:
            return None

        filename = f"{self.config_name}-v{version}.backup"
        return self.backup_directory / filename

    def validate_runtime_update_allowed(self) -> None:
        """
        Validate that runtime configuration updates are allowed.

        Raises:
            ModelOnexError: If runtime updates are not allowed
        """
        if not self.allow_runtime_updates:
            msg = "Runtime configuration updates are not allowed for this subcontract"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
            )

    def create_configuration_source(
        self,
        source_type: str,
        source_path: object | None = None,
        priority: int = 100,
        *,
        required: bool = False,
        watch_for_changes: bool = False,
        source_id: UUID | None = None,
    ) -> ModelConfigurationSource:
        """
        Create a new configuration source.

        Args:
            source_type: Type of configuration source
            source_path: Path or identifier for the source
            priority: Priority for merging (lower = higher priority)
            required: Whether this source is required
            watch_for_changes: Whether to monitor for changes
            source_id: Optional specific UUID for the source (auto-generated if not provided)

        Returns:
            ModelConfigurationSource instance
        """
        return ModelConfigurationSource(
            version=ModelSemVer(major=1, minor=0, patch=0),
            source_id=source_id or uuid4(),
            source_type=source_type,
            source_path=source_path,
            priority=priority,
            required=required,
            watch_for_changes=watch_for_changes,
        )

    def add_configuration_source(self, source: ModelConfigurationSource) -> None:
        """
        Add a configuration source to the subcontract.

        Args:
            source: Configuration source to add
        """
        # Validate priority uniqueness for required sources
        if source.required:
            existing_required_priorities = [
                src.priority for src in self.configuration_sources if src.required
            ]
            if source.priority in existing_required_priorities:
                msg = (
                    f"Required configuration source priority {source.priority} "
                    "already exists"
                )
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

        self.configuration_sources.append(source)

        # Sort by priority (lower priority = higher precedence)
        self.configuration_sources.sort(key=lambda x: x.priority)

    def remove_configuration_source(
        self,
        source_type: str,
        source_path: str | None = None,
    ) -> bool:
        """
        Remove a configuration source from the subcontract.

        Args:
            source_type: Type of configuration source to remove
            source_path: Path of source to remove (None matches any path)

        Returns:
            True if source was removed, False if not found
        """
        original_length = len(self.configuration_sources)

        if source_path is not None:
            # Remove specific source by type and path
            self.configuration_sources = [
                src
                for src in self.configuration_sources
                if not (
                    src.source_type == source_type and src.source_path == source_path
                )
            ]
        else:
            # Remove all sources of the specified type
            self.configuration_sources = [
                src
                for src in self.configuration_sources
                if src.source_type != source_type
            ]

        return len(self.configuration_sources) < original_length

    def get_configuration_source_by_id(
        self,
        source_id: UUID,
    ) -> ModelConfigurationSource | None:
        """
        Get a configuration source by its UUID.

        Args:
            source_id: UUID of the configuration source to find

        Returns:
            ModelConfigurationSource if found, None otherwise
        """
        for source in self.configuration_sources:
            if source.source_id == source_id:
                return source
        return None

    def get_configuration_sources_by_type(
        self,
        source_type: str,
    ) -> list[ModelConfigurationSource]:
        """
        Get all configuration sources of a specific type.

        Args:
            source_type: Type of configuration sources to retrieve

        Returns:
            List of configuration sources matching the type
        """
        return [
            source
            for source in self.configuration_sources
            if source.source_type == source_type
        ]
