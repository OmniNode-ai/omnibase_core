"""
Hub Contract Configuration Models for NodeHubBase.

These models support both existing contract formats (AI hub and Generation hub)
and provide a unified interface for contract-driven hub configuration.
"""

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class EnumHubCapability(str, Enum):
    """Hub capability types for different domains."""

    # Core hub capabilities
    TOOL_EXECUTION = "tool_execution"
    WORKFLOW_EXECUTION = "workflow_execution"
    EVENT_ROUTING = "event_routing"
    STATE_MANAGEMENT = "state_management"
    REMOTE_TOOLS = "remote_tools"
    HEALTH_MONITORING = "health_monitoring"
    PERFORMANCE_METRICS = "performance_metrics"
    EVENT_BUS_INTEGRATION = "event_bus_integration"

    # AI domain capabilities
    AI_TOOL_REGISTRY = "ai_tool_registry"
    TOOL_DISCOVERY = "tool_discovery"
    MCP_SERVER_INTEGRATION = "mcp_server_integration"

    # Canary domain capabilities
    CANARY_DEPLOYMENT = "canary_deployment"
    TESTING_ORCHESTRATION = "testing_orchestration"
    VALIDATION_WORKFLOWS = "validation_workflows"
    PROGRESSIVE_ROLLOUTS = "progressive_rollouts"
    ROLLBACK_AUTOMATION = "rollback_automation"


class EnumCoordinationMode(str, Enum):
    """Hub coordination modes."""

    EVENT_ROUTER = "event_router"
    WORKFLOW_ORCHESTRATOR = "workflow_orchestrator"
    META_HUB_ROUTER = "meta_hub_router"


class ModelHubHttpEndpoint(BaseModel):
    """HTTP endpoint configuration for hubs."""

    path: str = Field(..., description="Endpoint path")
    method: str = Field(default="GET", description="HTTP method")
    description: str | None = Field(None, description="Endpoint description")


class ModelHubWebSocketEndpoint(BaseModel):
    """WebSocket endpoint configuration for hubs."""

    path: str = Field(..., description="WebSocket path")
    description: str | None = Field(None, description="WebSocket description")


class ModelHubServiceConfiguration(BaseModel):
    """Service configuration section from contracts."""

    is_persistent_service: bool | None = Field(
        True,
        description="Whether hub runs as persistent service",
    )
    http_endpoints: list[ModelHubHttpEndpoint] | None = Field(
        default_factory=list,
        description="HTTP endpoints provided by hub",
    )
    websocket_endpoints: list[ModelHubWebSocketEndpoint] | None = Field(
        default_factory=list,
        description="WebSocket endpoints provided by hub",
    )
    default_port: int | None = Field(None, description="Default service port")


class ModelHubConfiguration(BaseModel):
    """Unified hub configuration supporting both contract formats."""

    # Core hub identity
    domain: str = Field(
        ...,
        description="Hub domain (e.g., 'generation', 'ai')",
        pattern=r"^[a-z_][a-z0-9_]*$",
    )

    # Service configuration
    service_port: int | None = Field(
        None,
        description="Port for hub HTTP service",
        ge=1024,
        le=65535,
    )

    # Hub capabilities and behavior
    coordination_mode: EnumCoordinationMode | None = Field(
        EnumCoordinationMode.EVENT_ROUTER,
        description="Hub coordination strategy",
    )

    capabilities: list[EnumHubCapability] | None = Field(
        default_factory=list,
        description="Hub capabilities",
    )

    priority: str | None = Field("normal", description="Hub execution priority")

    docker_enabled: bool | None = Field(
        False,
        description="Enable Docker container isolation",
    )

    # Tool management
    managed_tools: list[str] | None = Field(
        default_factory=list,
        description="Tools managed by this hub",
    )

    # Service registry configuration
    introspection_timeout: int | None = Field(
        30,
        description="Introspection timeout in seconds",
    )

    service_ttl: int | None = Field(300, description="Service TTL in seconds")

    auto_cleanup_interval: int | None = Field(
        60,
        description="Auto cleanup interval in seconds",
    )


class ModelUnifiedHubContract(BaseModel):
    """
    Unified hub contract model that can parse both AI and Generation hub formats.

    This model provides a standardized interface while supporting both:
    - Generation hub format: hub_configuration.domain + orchestration_workflows
    - AI hub format: service_configuration.default_port + tool_specification
    """

    # Hub configuration (primary)
    hub_configuration: ModelHubConfiguration | None = Field(
        None,
        description="Hub configuration (Generation hub format)",
    )

    # Service configuration (AI hub format)
    service_configuration: ModelHubServiceConfiguration | None = Field(
        None,
        description="Service configuration (AI hub format)",
    )

    # Tool specification (AI hub format)
    tool_specification: dict[str, Any] | None = Field(
        None,
        description="Tool specification from AI hub contracts",
    )

    # Workflows (Generation hub format)
    orchestration_workflows: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Orchestration workflows",
    )

    # Tool coordination (Generation hub format)
    tool_coordination: dict[str, Any] | None = Field(
        None,
        description="Tool coordination configuration",
    )

    # Tool execution (Generation hub format)
    tool_execution: dict[str, Any] | None = Field(
        None,
        description="Tool execution configuration",
    )

    # Contract metadata
    contract_metadata: dict[str, Any] | None = Field(
        None,
        description="Contract metadata",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_contract_format(cls, values):
        """Validate that we have either hub_configuration or service_configuration."""
        if isinstance(values, dict):
            hub_config = values.get("hub_configuration")
            service_config = values.get("service_configuration")

            if not hub_config and not service_config:
                msg = "Contract must have either hub_configuration or service_configuration"
                raise ValueError(
                    msg,
                )

        return values

    def get_unified_config(self) -> ModelHubConfiguration:
        """
        Get unified hub configuration from either format.

        Returns:
            ModelHubConfiguration with normalized settings
        """
        if self.hub_configuration:
            # Generation hub format - use directly
            return self.hub_configuration

        # AI hub format - convert to unified format
        domain = "unknown"
        service_port = None
        capabilities = []
        managed_tools = []

        # Extract domain from tool_specification if available
        if self.tool_specification:
            # Try to infer domain from tool name
            tool_name = self.tool_specification.get("tool_name", "")
            if "ai" in tool_name.lower():
                domain = "ai"
            elif "generation" in tool_name.lower():
                domain = "generation"

            # Extract capabilities
            spec_capabilities = self.tool_specification.get("capabilities", [])
            for cap in spec_capabilities:
                if cap in [e.value for e in EnumHubCapability]:
                    capabilities.append(EnumHubCapability(cap))

        # Extract port from service_configuration
        if self.service_configuration and self.service_configuration.default_port:
            service_port = self.service_configuration.default_port

        return ModelHubConfiguration(
            domain=domain,
            service_port=service_port,
            capabilities=capabilities,
            managed_tools=managed_tools,
            coordination_mode=EnumCoordinationMode.EVENT_ROUTER,
        )

    def get_domain(self) -> str:
        """Get hub domain from either format."""
        config = self.get_unified_config()
        return config.domain

    def get_service_port(self) -> int:
        """Get service port from either format."""
        config = self.get_unified_config()
        return config.service_port or 8080

    def get_managed_tools(self) -> list[str]:
        """Get managed tools from either format."""
        config = self.get_unified_config()
        return config.managed_tools or []

    def get_capabilities(self) -> list[EnumHubCapability]:
        """Get hub capabilities from either format."""
        config = self.get_unified_config()
        return config.capabilities or []

    def get_coordination_mode(self) -> EnumCoordinationMode:
        """Get coordination mode from either format."""
        config = self.get_unified_config()
        return config.coordination_mode or EnumCoordinationMode.EVENT_ROUTER

    @classmethod
    def from_dict(cls, contract_data: dict[str, Any]) -> "ModelUnifiedHubContract":
        """
        Create unified contract from raw dictionary data.

        Args:
            contract_data: Raw contract dictionary from YAML/JSON

        Returns:
            ModelUnifiedHubContract instance
        """
        # Extract known sections
        hub_config_data = contract_data.get("hub_configuration")
        service_config_data = contract_data.get("service_configuration")
        tool_spec_data = contract_data.get("tool_specification")

        # Convert to Pydantic models where possible
        hub_config = None
        if hub_config_data:
            hub_config = ModelHubConfiguration(**hub_config_data)

        service_config = None
        if service_config_data:
            service_config = ModelHubServiceConfiguration(**service_config_data)

        return cls(
            hub_configuration=hub_config,
            service_configuration=service_config,
            tool_specification=tool_spec_data,
            orchestration_workflows=contract_data.get("orchestration_workflows", {}),
            tool_coordination=contract_data.get("tool_coordination"),
            tool_execution=contract_data.get("tool_execution"),
            contract_metadata=contract_data.get("contract_metadata"),
        )

    @classmethod
    def from_yaml_file(cls, contract_path: Path) -> "ModelUnifiedHubContract":
        """
        Load unified contract from YAML file.

        Args:
            contract_path: Path to contract YAML file

        Returns:
            ModelUnifiedHubContract instance
        """
        from omnibase_core.model.core.model_generic_yaml import ModelGenericYaml
        from omnibase_core.utils.safe_yaml_loader import (
            load_and_validate_yaml_model,
        )

        if not contract_path.exists():
            msg = f"Contract file not found: {contract_path}"
            raise FileNotFoundError(msg)

        with open(contract_path) as f:
            # Load and validate YAML using Pydantic model

            yaml_model = load_and_validate_yaml_model(contract_path, ModelGenericYaml)

            contract_data = yaml_model.model_dump()

        return cls.from_dict(contract_data)
