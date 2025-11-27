"""
Group Manifest Model - Tier 1 Metadata

Pydantic model for group-level metadata in the three-tier metadata system.
Represents the highest level of organization for ONEX tool groups.
"""

from datetime import datetime

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Import extracted classes
from omnibase_core.enums.enum_group_status import EnumGroupStatus
from omnibase_core.enums.enum_security_profile import EnumSecurityProfile
from omnibase_core.models.core.model_group_dependency import ModelGroupDependency
from omnibase_core.models.core.model_group_manifest_config import ModelConfig
from omnibase_core.models.core.model_group_service_configuration import (
    ModelGroupServiceConfiguration,
)
from omnibase_core.models.core.model_group_tool import ModelGroupTool
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import SemVerField


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
        ...,  # REQUIRED - specify in contract
        description="Tool group blueprint version followed",
    )
    metadata_schema_version: SemVerField = Field(
        ...,  # REQUIRED - specify in contract
        description="Metadata schema version",
    )

    @field_validator("total_tools", "active_tools")
    @classmethod
    def validate_tool_counts(cls, v: int) -> int:
        """Validate tool count is non-negative."""
        if v < 0:
            msg = "Tool counts must be non-negative"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
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
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("tools")
    @classmethod
    def validate_tools_list(cls, v: list[ModelGroupTool]) -> list[ModelGroupTool]:
        """Validate tools list[Any]consistency."""
        if not v:
            msg = "tools list[Any]cannot be empty"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        # Check for duplicate tool names
        tool_names = [tool.tool_name for tool in v]
        if len(tool_names) != len(set(tool_names)):
            msg = "Duplicate tool names found in tools list[Any]"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

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


# Public API exports
__all__ = [
    "ModelGroupManifest",
    "ModelConfig",
    "EnumGroupStatus",
    "EnumSecurityProfile",
    "ModelGroupDependency",
    "ModelGroupServiceConfiguration",
    "ModelGroupTool",
]
