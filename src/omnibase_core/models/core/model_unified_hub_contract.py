#!/usr/bin/env python3
"""
Unified Hub Contract Model - ONEX Standards Compliant.

Strongly-typed model that can parse both AI and Generation hub formats.
"""

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from omnibase_core.enums.enum_coordination_mode import EnumCoordinationMode
from omnibase_core.enums.enum_hub_capability import EnumHubCapability
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_hub_configuration import ModelHubConfiguration
from omnibase_core.models.core.model_hub_service_configuration import (
    ModelHubServiceConfiguration,
)

if TYPE_CHECKING:
    pass


class ModelUnifiedHubContract(BaseModel):
    """
    Unified hub contract model that can parse both AI and Generation hub formats.

    This model provides a standardized interface while supporting both:
    - Generation hub format: hub_configuration.domain + orchestration_workflows
    - AI hub format: service_configuration.default_port + tool_specification
    """

    # Hub configuration (primary)
    hub_configuration: ModelHubConfiguration | None = Field(
        default=None,
        description="Hub configuration (Generation hub format)",
    )

    # Service configuration (AI hub format)
    service_configuration: ModelHubServiceConfiguration | None = Field(
        default=None,
        description="Service configuration (AI hub format)",
    )

    # Tool specification (AI hub format)
    tool_specification: dict[str, Any] | None = Field(
        default=None,
        description="Tool specification from AI hub contracts",
    )

    # Workflows (Generation hub format)
    orchestration_workflows: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Orchestration workflows",
    )

    # Tool coordination (Generation hub format)
    tool_coordination: dict[str, Any] | None = Field(
        default=None,
        description="Tool coordination configuration",
    )

    # Tool execution (Generation hub format)
    tool_execution: dict[str, Any] | None = Field(
        default=None,
        description="Tool execution configuration",
    )

    # Contract metadata
    contract_metadata: dict[str, Any] | None = Field(
        default=None,
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
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
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
        # Generate UUID for domain
        domain_hash = hashlib.sha256(domain.encode()).hexdigest()
        domain_id = UUID(
            f"{domain_hash[:8]}-{domain_hash[8:12]}-{domain_hash[12:16]}-{domain_hash[16:20]}-{domain_hash[20:32]}"
        )

        # Generate UUIDs for managed tools
        managed_tool_ids = []
        for tool in managed_tools:
            tool_hash = hashlib.sha256(tool.encode()).hexdigest()
            tool_id = UUID(
                f"{tool_hash[:8]}-{tool_hash[8:12]}-{tool_hash[12:16]}-{tool_hash[16:20]}-{tool_hash[20:32]}"
            )
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
        Create unified contract from raw dict[str, Any]ionary data.

        Args:
            contract_data: Raw contract dict[str, Any]ionary from YAML/JSON

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
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Failed to load contract from {contract_path}: {e}",
            ) from e
