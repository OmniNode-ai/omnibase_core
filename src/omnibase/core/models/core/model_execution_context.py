"""
Execution Context Model

Execution environment context for CLI commands including environment,
timeouts, retry configuration, and debug settings.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from omnibase.model.core.model_duration import ModelDuration
from omnibase.model.core.model_environment import ModelEnvironment
from omnibase.model.core.model_execution_mode import ModelExecutionMode


class ModelContextMetadata(BaseModel):
    """Metadata for execution context."""

    # Request tracking
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    request_source: Optional[str] = Field(None, description="Source of the request")
    request_timestamp: Optional[str] = Field(None, description="Request timestamp")

    # Authentication context
    auth_method: Optional[str] = Field(None, description="Authentication method used")
    auth_provider: Optional[str] = Field(None, description="Authentication provider")
    permissions: List[str] = Field(
        default_factory=list, description="Granted permissions"
    )

    # Execution constraints
    max_memory_mb: Optional[int] = Field(None, description="Maximum memory allowed")
    max_cpu_percent: Optional[float] = Field(
        None, description="Maximum CPU usage allowed"
    )
    priority_level: Optional[str] = Field(None, description="Execution priority level")

    # Feature flags
    enabled_features: List[str] = Field(
        default_factory=list, description="Enabled features"
    )
    disabled_features: List[str] = Field(
        default_factory=list, description="Disabled features"
    )
    experimental_features: List[str] = Field(
        default_factory=list, description="Experimental features"
    )

    # Monitoring and telemetry
    trace_flags: Optional[str] = Field(None, description="Distributed tracing flags")
    baggage_items: Dict[str, str] = Field(
        default_factory=dict, description="OpenTelemetry baggage"
    )
    parent_span_id: Optional[str] = Field(
        None, description="Parent span ID for tracing"
    )

    # Custom metadata for extensibility
    custom_tags: Dict[str, str] = Field(default_factory=dict, description="Custom tags")
    custom_metrics: Optional[Dict[str, float]] = Field(
        None, description="Custom metrics"
    )


class ModelExecutionContext(BaseModel):
    """
    Execution environment context for CLI commands.

    This model captures the execution environment including mode,
    environment configuration, timeouts, and debug settings.
    """

    execution_mode: ModelExecutionMode = Field(
        default=ModelExecutionMode.DIRECT(),
        description="Execution mode (direct, inmemory, kafka)",
    )

    environment: ModelEnvironment = Field(..., description="Environment configuration")

    timeout: ModelDuration = Field(
        default_factory=lambda: ModelDuration(milliseconds=30000),
        description="Execution timeout",
    )

    retry_attempts: int = Field(
        default=3, description="Number of retry attempts on failure", ge=0, le=10
    )

    debug_enabled: bool = Field(
        default=False, description="Whether debug mode is enabled"
    )

    trace_enabled: bool = Field(
        default=False, description="Whether execution tracing is enabled"
    )

    dry_run: bool = Field(
        default=False, description="Whether this is a dry run (no actual execution)"
    )

    verbose: bool = Field(
        default=False, description="Whether verbose output is enabled"
    )

    working_directory: Optional[str] = Field(
        None, description="Working directory for command execution"
    )

    environment_variables: Dict[str, str] = Field(
        default_factory=dict, description="Additional environment variables"
    )

    execution_metadata: ModelContextMetadata = Field(
        default_factory=ModelContextMetadata, description="Execution metadata"
    )

    user_id: Optional[str] = Field(
        None, description="User ID for audit and permissions"
    )

    session_id: Optional[str] = Field(
        None, description="Session ID for tracking related commands"
    )

    correlation_id: Optional[str] = Field(
        None, description="Correlation ID for distributed tracing"
    )

    def is_async_mode(self) -> bool:
        """Check if execution mode is asynchronous."""
        return self.execution_mode in [
            ModelExecutionMode.INMEMORY(),
            ModelExecutionMode.KAFKA(),
        ]

    def is_distributed_mode(self) -> bool:
        """Check if execution mode is distributed."""
        return self.execution_mode == ModelExecutionMode.KAFKA()

    def is_local_mode(self) -> bool:
        """Check if execution mode is local."""
        return self.execution_mode in [
            ModelExecutionMode.DIRECT(),
            ModelExecutionMode.INMEMORY(),
        ]

    def get_timeout_ms(self) -> int:
        """Get timeout in milliseconds."""
        return self.timeout.total_milliseconds()

    def should_retry(self) -> bool:
        """Check if retries are enabled."""
        return self.retry_attempts > 0

    def add_environment_variable(self, key: str, value: str) -> None:
        """Add an environment variable."""
        self.environment_variables[key] = value

    def add_metadata(self, key: str, value: Any) -> None:
        """Add execution metadata."""
        # Use setattr for known fields or add to custom tags
        if hasattr(self.execution_metadata, key):
            setattr(self.execution_metadata, key, value)
        else:
            # Convert to string and add to custom tags
            self.execution_metadata.custom_tags[key] = str(value)

    def get_environment_variable(
        self, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Get environment variable value."""
        return self.environment_variables.get(key, default)

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get execution metadata value."""
        # Check known fields first
        if hasattr(self.execution_metadata, key):
            return getattr(self.execution_metadata, key, default)
        # Check custom tags
        return self.execution_metadata.custom_tags.get(key, default)

    def create_child_context(self, **overrides) -> "ModelExecutionContext":
        """Create a child context with optional overrides."""
        data = self.model_dump()
        data.update(overrides)
        return ModelExecutionContext(**data)

    def to_environment_dict(self) -> Dict[str, str]:
        """Convert to environment variables dictionary."""
        env_dict = self.environment_variables.copy()

        # Add standard execution context variables
        env_dict["ONEX_EXECUTION_MODE"] = self.execution_mode.value
        env_dict["ONEX_ENVIRONMENT"] = self.environment.name
        env_dict["ONEX_DEBUG_ENABLED"] = str(self.debug_enabled).lower()
        env_dict["ONEX_TRACE_ENABLED"] = str(self.trace_enabled).lower()
        env_dict["ONEX_DRY_RUN"] = str(self.dry_run).lower()
        env_dict["ONEX_VERBOSE"] = str(self.verbose).lower()
        env_dict["ONEX_TIMEOUT_MS"] = str(self.get_timeout_ms())
        env_dict["ONEX_RETRY_ATTEMPTS"] = str(self.retry_attempts)

        if self.user_id:
            env_dict["ONEX_USER_ID"] = self.user_id
        if self.session_id:
            env_dict["ONEX_SESSION_ID"] = self.session_id
        if self.correlation_id:
            env_dict["ONEX_CORRELATION_ID"] = self.correlation_id
        if self.working_directory:
            env_dict["ONEX_WORKING_DIRECTORY"] = self.working_directory

        return env_dict

    @classmethod
    def create_default(
        cls,
        environment_name: str = "development",
        execution_mode: ModelExecutionMode = ModelExecutionMode.DIRECT(),
    ) -> "ModelExecutionContext":
        """Create a default execution context."""
        environment = ModelEnvironment.create_default(environment_name)
        return cls(execution_mode=execution_mode, environment=environment)

    @classmethod
    def create_debug(
        cls, environment_name: str = "development"
    ) -> "ModelExecutionContext":
        """Create a debug execution context."""
        context = cls.create_default(environment_name)
        context.debug_enabled = True
        context.trace_enabled = True
        context.verbose = True
        return context

    @classmethod
    def create_production(
        cls, environment_name: str = "production"
    ) -> "ModelExecutionContext":
        """Create a production execution context."""
        environment = ModelEnvironment.create_default(environment_name)
        return cls(
            execution_mode=ModelExecutionMode.KAFKA(),
            environment=environment,
            timeout=ModelDuration(milliseconds=60000),  # Longer timeout for production
            retry_attempts=5,  # More retries for production
        )
