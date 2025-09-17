"""
Group Manifest Model - Tier 1 Metadata

Pydantic model for group-level metadata in the three-tier metadata system.
Represents the highest level of organization for ONEX tool groups.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator
from pydantic.dataclasses import ValidationInfo

from omnibase_core.models.core.model_semver import ModelSemVer, SemVerField


class EnumSecurityProfile(str, Enum):
    """Security profile levels for progressive security implementation."""

    SP0_BOOTSTRAP = "SP0_BOOTSTRAP"
    SP1_BASELINE = "SP1_BASELINE"
    SP2_PRODUCTION = "SP2_PRODUCTION"
    SP3_HIGH_ASSURANCE = "SP3_HIGH_ASSURANCE"


class EnumGroupStatus(str, Enum):
    """Group lifecycle status values."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    MAINTENANCE = "maintenance"


class ModelGroupServiceEndpoint(BaseModel):
    """HTTP endpoint definition for group services."""

    path: str = Field(description="HTTP endpoint path")
    method: str = Field(description="HTTP method (GET, POST, PUT, DELETE)")
    description: str = Field(description="Endpoint purpose and functionality")
    delegation_target: str | None = Field(
        default=None,
        description="Tool to delegate requests to",
    )
    authentication_required: bool = Field(
        default=True,
        description="Whether authentication is required",
    )


class ModelGroupServiceConfiguration(BaseModel):
    """Service configuration for tool groups that host HTTP services."""

    is_persistent_service: bool = Field(
        description="Whether this group hosts a persistent HTTP service",
    )
    default_port: int | None = Field(
        default=None,
        description="Default HTTP port for the group service",
    )
    http_endpoints: list[ModelGroupServiceEndpoint] = Field(
        default_factory=list,
        description="HTTP endpoints provided by group",
    )
    websocket_endpoints: list[ModelGroupServiceEndpoint] = Field(
        default_factory=list,
        description="WebSocket endpoints provided by group",
    )
    health_check_path: str = Field(
        default="/health",
        description="Health check endpoint path",
    )
    metrics_path: str = Field(default="/metrics", description="Metrics endpoint path")


class ModelGroupDependency(BaseModel):
    """External dependency required by the tool group."""

    name: str = Field(description="Dependency name")
    type: str = Field(description="Dependency type (service, library, protocol)")
    version_requirement: str | None = Field(
        default=None,
        description="Version requirement specification",
    )
    optional: bool = Field(default=False, description="Whether dependency is optional")
    description: str = Field(description="Dependency purpose and usage")


class ModelGroupTool(BaseModel):
    """Tool reference within a group."""

    tool_name: str = Field(description="Name of the tool")
    current_version: SemVerField = Field(description="Current active version")
    status: EnumGroupStatus = Field(description="Tool status within group")
    description: str = Field(description="Tool purpose and capabilities")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Tool capabilities list",
    )


class ModelGroupManifest(BaseModel):
    """
    Tier 1: Group-level metadata model.

    Defines group-wide configuration, tool catalog, shared dependencies,
    and service configuration for ONEX tool groups.
    """

    # === GROUP IDENTITY ===
    group_name: str = Field(description="Unique tool group identifier")
    group_version: SemVerField = Field(
        description="Group version (semantic versioning)",
    )
    description: str = Field(description="Group purpose and functionality overview")
    created_date: datetime = Field(description="Group creation timestamp")
    last_modified_date: datetime = Field(description="Last modification timestamp")

    # === GROUP STATUS ===
    status: EnumGroupStatus = Field(description="Current group lifecycle status")
    canonical_reference: bool = Field(
        default=False,
        description="Whether this group serves as canonical reference for others",
    )

    # === TOOLS CATALOG ===
    tools: list[ModelGroupTool] = Field(
        description="Catalog of tools within this group",
    )
    total_tools: int = Field(description="Total number of tools in group")
    active_tools: int = Field(description="Number of active tools")

    # === SHARED CONFIGURATION ===
    shared_dependencies: list[ModelGroupDependency] = Field(
        default_factory=list,
        description="Group-wide dependencies",
    )
    shared_protocols: list[str] = Field(
        default_factory=list,
        description="Shared protocol interfaces",
    )
    shared_models: list[str] = Field(
        default_factory=list,
        description="Shared Pydantic models",
    )

    # === SERVICE CONFIGURATION ===
    service_configuration: ModelGroupServiceConfiguration | None = Field(
        default=None,
        description="HTTP service configuration if applicable",
    )

    # === SECURITY PROFILE ===
    security_profile: EnumSecurityProfile = Field(
        description="Security profile level for the group",
    )
    security_requirements: dict[str, str] = Field(
        default_factory=dict,
        description="Specific security requirements",
    )

    # === DEPLOYMENT CONFIGURATION ===
    deployment_configuration: dict[str, str] = Field(
        default_factory=dict,
        description="Deployment-specific settings",
    )
    docker_configuration: dict[str, str] | None = Field(
        default=None,
        description="Docker deployment configuration",
    )

    # === M1 INTEGRATION ===
    m1_compliance: bool = Field(
        default=True,
        description="Whether group follows M1 standards",
    )
    envelope_pattern_enabled: bool = Field(
        default=True,
        description="Whether M1 envelope/reply pattern is used",
    )

    # === METADATA VALIDATION ===
    blueprint_version: SemVerField = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Tool group blueprint version followed",
    )
    metadata_schema_version: SemVerField = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Metadata schema version",
    )

    class Config:
        """Pydantic configuration."""

        frozen = True
        use_enum_values = True

    @field_validator("total_tools", "active_tools")
    @classmethod
    def validate_tool_counts(cls, v: int) -> int:
        """Validate tool count is non-negative."""
        if v < 0:
            msg = "Tool counts must be non-negative"
            raise ValueError(msg)
        return v

    @field_validator("active_tools")
    @classmethod
    def validate_active_tools_count(
        cls,
        v: int,
        info: ValidationInfo,
    ) -> int:
        """Validate active tools count doesn't exceed total."""
        total = info.data.get("total_tools", 0)
        if not isinstance(total, int):
            total = 0
        if v > total:
            msg = "active_tools cannot exceed total_tools"
            raise ValueError(msg)
        return v

    @field_validator("tools")
    @classmethod
    def validate_tools_list(cls, v: list[ModelGroupTool]) -> list[ModelGroupTool]:
        """Validate tools list consistency."""
        if not v:
            msg = "tools list cannot be empty"
            raise ValueError(msg)

        # Check for duplicate tool names
        tool_names = [tool.tool_name for tool in v]
        if len(tool_names) != len(set(tool_names)):
            msg = "Duplicate tool names found in tools list"
            raise ValueError(msg)

        return v

    def get_tools_by_status(self, status: EnumGroupStatus) -> list[ModelGroupTool]:
        """Get all tools with specified status."""
        return [tool for tool in self.tools if tool.status == status]

    def get_tool_by_name(self, tool_name: str) -> ModelGroupTool | None:
        """Get tool by name."""
        for tool in self.tools:
            if tool.tool_name == tool_name:
                return tool
        return None

    def is_security_compliant(self) -> bool:
        """Check if group meets minimum security requirements."""
        return (
            self.security_profile
            in [
                EnumSecurityProfile.SP0_BOOTSTRAP,
                EnumSecurityProfile.SP1_BASELINE,
                EnumSecurityProfile.SP2_PRODUCTION,
                EnumSecurityProfile.SP3_HIGH_ASSURANCE,
            ]
            and self.m1_compliance
            and self.envelope_pattern_enabled
        )
