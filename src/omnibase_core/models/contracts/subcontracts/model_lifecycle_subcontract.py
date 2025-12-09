"""
Lifecycle Subcontract Model.



Dedicated subcontract model for node lifecycle management providing:
- Node startup and shutdown timeout configuration
- Graceful shutdown behavior controls
- Lifecycle hook registration for pre/post startup and shutdown
- Event emission configuration for lifecycle events
- Node registration and deregistration behavior

This model is composed into node contracts that require lifecycle management,
providing clean separation between node logic and lifecycle behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelLifecycleSubcontract(BaseModel):
    """
    Lifecycle subcontract model for node lifecycle management.

    Comprehensive lifecycle configuration providing startup/shutdown timeouts,
    graceful shutdown controls, lifecycle hook registration, and event emission
    configuration following ONEX standards.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Startup configuration
    startup_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=3600.0,
        description="Maximum time allowed for node startup in seconds",
    )

    startup_retry_enabled: bool = Field(
        default=True,
        description="Whether to retry startup on failure",
    )

    max_startup_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of startup retry attempts",
    )

    startup_retry_delay_seconds: float = Field(
        default=5.0,
        ge=1.0,
        le=60.0,
        description="Delay between startup retry attempts",
    )

    # Shutdown configuration
    shutdown_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=3600.0,
        description="Maximum time allowed for graceful shutdown in seconds",
    )

    enable_graceful_shutdown: bool = Field(
        default=True,
        description="Enable graceful shutdown with proper resource cleanup",
    )

    force_shutdown_after_timeout: bool = Field(
        default=True,
        description="Force shutdown if graceful shutdown exceeds timeout",
    )

    # Node registration and deregistration
    auto_register_on_startup: bool = Field(
        default=True,
        description="Automatically register node on event bus during startup",
    )

    auto_deregister_on_shutdown: bool = Field(
        default=True,
        description="Automatically deregister node from event bus during shutdown",
    )

    publish_shutdown_event: bool = Field(
        default=True,
        description="Publish NODE_SHUTDOWN event during deregistration",
    )

    # Lifecycle hooks
    pre_startup_hooks: list[str] = Field(
        default_factory=list,
        description="List of hook function names to execute before startup",
    )

    post_startup_hooks: list[str] = Field(
        default_factory=list,
        description="List of hook function names to execute after startup",
    )

    pre_shutdown_hooks: list[str] = Field(
        default_factory=list,
        description="List of hook function names to execute before shutdown",
    )

    post_shutdown_hooks: list[str] = Field(
        default_factory=list,
        description="List of hook function names to execute after shutdown",
    )

    # Lifecycle event emission
    emit_lifecycle_events: bool = Field(
        default=True,
        description="Emit NODE_START, NODE_SUCCESS, NODE_FAILURE events",
    )

    emit_node_announce: bool = Field(
        default=True,
        description="Emit NODE_ANNOUNCE event during registration",
    )

    emit_node_shutdown: bool = Field(
        default=True,
        description="Emit NODE_SHUTDOWN event during deregistration",
    )

    # Hook execution configuration
    hook_timeout_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=300.0,
        description="Maximum time allowed for each hook execution",
    )

    fail_fast_on_hook_error: bool = Field(
        default=False,
        description="Fail startup/shutdown immediately if any hook fails",
    )

    continue_on_hook_timeout: bool = Field(
        default=True,
        description="Continue lifecycle process if hook execution times out",
    )

    # Resource cleanup
    cleanup_event_handlers: bool = Field(
        default=True,
        description="Clean up event handlers during shutdown",
    )

    cleanup_resources: bool = Field(
        default=True,
        description="Clean up managed resources during shutdown",
    )

    cleanup_timeout_seconds: float = Field(
        default=15.0,
        ge=1.0,
        le=300.0,
        description="Maximum time allowed for resource cleanup",
    )

    # Monitoring and logging
    log_lifecycle_events: bool = Field(
        default=True,
        description="Log lifecycle state transitions and events",
    )

    log_hook_execution: bool = Field(
        default=True,
        description="Log hook execution start/completion/errors",
    )

    detailed_lifecycle_logging: bool = Field(
        default=False,
        description="Enable verbose logging for lifecycle operations",
    )

    # Health checks
    startup_health_check_enabled: bool = Field(
        default=True,
        description="Verify node health after startup",
    )

    shutdown_health_check_enabled: bool = Field(
        default=False,
        description="Verify clean shutdown (resource deallocation)",
    )

    health_check_timeout_seconds: float = Field(
        default=5.0,
        ge=1.0,
        le=60.0,
        description="Maximum time allowed for health checks",
    )

    @field_validator(
        "pre_startup_hooks",
        "post_startup_hooks",
        "pre_shutdown_hooks",
        "post_shutdown_hooks",
    )
    @classmethod
    def validate_hook_names(cls, hooks: list[str]) -> list[str]:
        """
        Validate that hook names are valid Python function identifiers.

        Args:
            hooks: List of hook function names

        Returns:
            list[str]: Validated hook names

        Raises:
            ModelOnexError: If any hook name is not a valid identifier
        """
        for hook in hooks:
            if not hook:
                msg = "Hook name cannot be empty string"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "field_validation",
                            ),
                            "field": ModelSchemaValue.from_value("lifecycle_hooks"),
                        },
                    ),
                )

            if not hook.isidentifier():
                msg = f"Hook name '{hook}' must be a valid Python identifier"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "field_validation",
                            ),
                            "field": ModelSchemaValue.from_value("lifecycle_hooks"),
                            "invalid_hook": ModelSchemaValue.from_value(hook),
                        },
                    ),
                )

        return hooks

    @model_validator(mode="after")
    def validate_lifecycle_configuration(self) -> Self:
        """
        Comprehensive validation of lifecycle configuration.

        Validates:
        - shutdown_timeout_seconds >= startup_timeout_seconds (graceful shutdown)
        - hook_timeout_seconds < startup_timeout_seconds and shutdown_timeout_seconds
        - cleanup_timeout_seconds <= shutdown_timeout_seconds
        - health_check_timeout_seconds < startup_timeout_seconds
        """
        # Validate shutdown timeout allows adequate time for cleanup
        if self.shutdown_timeout_seconds < self.startup_timeout_seconds:
            msg = (
                f"shutdown_timeout_seconds ({self.shutdown_timeout_seconds}) "
                f"should be >= startup_timeout_seconds ({self.startup_timeout_seconds}) "
                "to allow proper cleanup"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value(
                            "shutdown_timeout_seconds"
                        ),
                        "shutdown_timeout": ModelSchemaValue.from_value(
                            self.shutdown_timeout_seconds
                        ),
                        "startup_timeout": ModelSchemaValue.from_value(
                            self.startup_timeout_seconds
                        ),
                    },
                ),
            )

        # Validate hook timeout is reasonable relative to lifecycle timeouts
        if self.hook_timeout_seconds >= self.startup_timeout_seconds:
            msg = (
                f"hook_timeout_seconds ({self.hook_timeout_seconds}) "
                f"must be < startup_timeout_seconds ({self.startup_timeout_seconds})"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("hook_timeout_seconds"),
                    },
                ),
            )

        if self.hook_timeout_seconds >= self.shutdown_timeout_seconds:
            msg = (
                f"hook_timeout_seconds ({self.hook_timeout_seconds}) "
                f"must be < shutdown_timeout_seconds ({self.shutdown_timeout_seconds})"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("hook_timeout_seconds"),
                    },
                ),
            )

        # Validate cleanup timeout doesn't exceed shutdown timeout
        if self.cleanup_timeout_seconds > self.shutdown_timeout_seconds:
            msg = (
                f"cleanup_timeout_seconds ({self.cleanup_timeout_seconds}) "
                f"must be <= shutdown_timeout_seconds ({self.shutdown_timeout_seconds})"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("cleanup_timeout_seconds"),
                    },
                ),
            )

        # Validate health check timeout is reasonable
        if self.health_check_timeout_seconds >= self.startup_timeout_seconds:
            msg = (
                f"health_check_timeout_seconds ({self.health_check_timeout_seconds}) "
                f"must be < startup_timeout_seconds ({self.startup_timeout_seconds})"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value(
                            "health_check_timeout_seconds"
                        ),
                    },
                ),
            )

        # Validate event emission configuration consistency
        if self.emit_node_announce and not self.auto_register_on_startup:
            msg = "emit_node_announce requires auto_register_on_startup to be enabled"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("emit_node_announce"),
                    },
                ),
            )

        if self.emit_node_shutdown and not self.auto_deregister_on_shutdown:
            msg = (
                "emit_node_shutdown requires auto_deregister_on_shutdown to be enabled"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("emit_node_shutdown"),
                    },
                ),
            )

        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,  # Validate on attribute assignment
    )
