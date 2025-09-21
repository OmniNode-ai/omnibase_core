"""
Hub Contract Configuration Models for NodeHubBase.

These models support both existing contract formats (AI hub and Generation hub)
and provide a unified interface for contract-driven hub configuration.
"""

from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

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
    domain_id: UUID = Field(
        ...,
        description="UUID of the hub domain",
    )

    domain_display_name: str | None = Field(
        None,
        description="Human-readable domain name (e.g., 'generation', 'ai')",
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

    @classmethod
    def create_with_legacy_domain(
        cls,
        domain_name: str,
        service_port: int | None = None,
        managed_tool_names: list[str] | None = None,
        **kwargs: Any,
    ) -> "ModelHubConfiguration":
        """Factory method to create hub configuration with legacy domain name."""
        import hashlib

        # Generate UUID for domain
        domain_hash = hashlib.sha256(domain_name.encode()).hexdigest()
        domain_id = UUID(f"{domain_hash[:8]}-{domain_hash[8:12]}-{domain_hash[12:16]}-{domain_hash[16:20]}-{domain_hash[20:32]}")

        # Generate UUIDs for managed tools
        managed_tool_ids = []
        tool_display_names = managed_tool_names or []
        for tool_name in tool_display_names:
            tool_hash = hashlib.sha256(tool_name.encode()).hexdigest()
            tool_id = UUID(f"{tool_hash[:8]}-{tool_hash[8:12]}-{tool_hash[12:16]}-{tool_hash[16:20]}-{tool_hash[20:32]}")
            managed_tool_ids.append(tool_id)

        return cls(
            domain_id=domain_id,
            domain_display_name=domain_name,
            service_port=service_port,
            managed_tool_ids=managed_tool_ids,
            managed_tool_display_names=tool_display_names,
            **kwargs,
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
    managed_tool_ids: list[UUID] | None = Field(
        default_factory=list,
        description="UUIDs of tools managed by this hub",
    )

    managed_tool_display_names: list[str] | None = Field(
        default_factory=list,
        description="Human-readable names of managed tools",
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

    @property
    def domain(self) -> str:
        """Backward compatibility property for domain."""
        return self.domain_display_name or f"domain_{str(self.domain_id)[:8]}"

    @domain.setter
    def domain(self, value: str) -> None:
        """Backward compatibility setter for domain."""
        self.domain_display_name = value

    @property
    def managed_tools(self) -> list[str]:
        """Backward compatibility property for managed_tools."""
        if self.managed_tool_display_names:
            return self.managed_tool_display_names
        return [f"tool_{str(tool_id)[:8]}" for tool_id in (self.managed_tool_ids or [])]

    @managed_tools.setter
    def managed_tools(self, value: list[str]) -> None:
        """Backward compatibility setter for managed_tools."""
        self.managed_tool_display_names = value


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
        managed_tools: list[str] = []

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

        # Convert domain and tools to UUID format
        import hashlib

        # Generate UUID for domain
        domain_hash = hashlib.sha256(domain.encode()).hexdigest()
        domain_id = UUID(f"{domain_hash[:8]}-{domain_hash[8:12]}-{domain_hash[12:16]}-{domain_hash[16:20]}-{domain_hash[20:32]}")

        # Generate UUIDs for managed tools
        managed_tool_ids = []
        for tool in managed_tools:
            tool_hash = hashlib.sha256(tool.encode()).hexdigest()
            tool_id = UUID(f"{tool_hash[:8]}-{tool_hash[8:12]}-{tool_hash[12:16]}-{tool_hash[16:20]}-{tool_hash[20:32]}")
            managed_tool_ids.append(tool_id)

        return ModelHubConfiguration(
            domain_id=domain_id,
            domain_display_name=domain,
            service_port=service_port,
            capabilities=capabilities,
            managed_tool_ids=managed_tool_ids,
            managed_tool_display_names=managed_tools,
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
        Load unified contract from YAML file with proper validation.

        Args:
            contract_path: Path to contract YAML file

        Returns:
            ModelUnifiedHubContract instance
        """
        from omnibase_core.utils.safe_yaml_loader import load_and_validate_yaml_model

        try:
            # Use centralized YAML loading with full Pydantic validation
            return load_and_validate_yaml_model(contract_path, cls)
        except Exception as e:
            raise ValueError(
                f"Failed to load contract from {contract_path}: {e}"
            ) from e
