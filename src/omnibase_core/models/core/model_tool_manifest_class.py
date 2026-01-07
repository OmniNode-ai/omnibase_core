"""
Tool Manifest Model - Main Class.

Tier 2: Tool-level metadata model with comprehensive tool definition.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.typed_dict_tool_comprehensive_summary import (
    TypedDictToolComprehensiveSummary,
)
from omnibase_core.types.typed_dict_tool_resource_summary import (
    TypedDictToolResourceSummary,
)

if TYPE_CHECKING:
    from omnibase_core.enums.enum_tool_manifest import (
        EnumBusinessLogicPattern,
        EnumNodeType,
        EnumToolStatus,
        EnumVersionStatus,
    )
    from omnibase_core.models.core.model_tool_capability import ModelToolCapability
    from omnibase_core.models.core.model_tool_dependency import ModelToolDependency
    from omnibase_core.models.core.model_tool_integration import ModelToolIntegration
    from omnibase_core.models.core.model_tool_security import ModelToolSecurity
    from omnibase_core.models.core.model_tool_testing import ModelToolTesting
    from omnibase_core.models.core.model_tool_version import ModelToolVersion


class ModelToolManifest(BaseModel):
    """
    Tier 2: Tool-level metadata model.

    Defines tool-specific configuration, version catalog, dependencies,
    capabilities, and integration requirements.
    """

    # === TOOL IDENTITY ===
    tool_name: str = Field(description="Unique tool identifier within group")
    description: str = Field(description="Tool purpose and functionality")
    author: str = Field(default="ONEX Framework Team", description="Tool author")
    created_date: str = Field(description="Tool creation timestamp")
    last_modified_date: str = Field(description="Last modification timestamp")

    # === TOOL CLASSIFICATION ===
    node_type: "EnumNodeType" = Field(description="ONEX node type classification")
    business_logic_pattern: "EnumBusinessLogicPattern" = Field(
        description="Business logic pattern classification",
    )
    meta_type: str = Field(default="tool", description="Meta-type classification")
    runtime_language_hint: str = Field(
        default="python>=3.11",
        description="Runtime language requirement",
    )

    # === TOOL STATUS ===
    status: "EnumToolStatus" = Field(description="Current tool lifecycle status")
    lifecycle: str = Field(default="active", description="Tool lifecycle state")

    # === VERSION CATALOG ===
    current_stable_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Current stable version identifier",
    )
    current_development_version: ModelSemVer | None = Field(
        default=None,
        description="Current development version identifier",
    )
    versions: list["ModelToolVersion"] = Field(
        description="Available versions with lifecycle information",
    )

    # === CAPABILITIES ===
    capabilities: list["ModelToolCapability"] = Field(
        description="Tool capabilities and operations",
    )
    protocols_supported: list[str] = Field(
        default_factory=list,
        description="Supported protocol interfaces",
    )

    # === DEPENDENCIES ===
    dependencies: list["ModelToolDependency"] = Field(
        default_factory=list,
        description="Tool-specific dependencies",
    )

    # === SERVICE INTEGRATION ===
    integration: "ModelToolIntegration" = Field(
        description="Service integration configuration",
    )

    # === EXECUTION METADATA ===
    execution_mode: str = Field(
        default="async",
        description="Execution mode (sync/async)",
    )
    max_memory_mb: int = Field(default=256, description="Maximum memory usage in MB")
    max_cpu_percent: int = Field(default=50, description="Maximum CPU usage percentage")
    timeout_seconds: int = Field(
        default=60,
        description="Default operation timeout in seconds",
    )

    # === TESTING CONFIGURATION ===
    testing: "ModelToolTesting" = Field(
        description="Testing requirements and configuration",
    )

    # === SECURITY CONFIGURATION ===
    security: "ModelToolSecurity" = Field(
        description="Security requirements and configuration",
    )

    # === METADATA VALIDATION ===
    schema_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Tool manifest schema version",
    )
    uuid: str | None = Field(
        default=None,
        description="Unique identifier for tool instance",
    )
    hash: str | None = Field(
        default=None,
        description="Content hash for integrity verification",
    )

    @field_validator(
        "current_stable_version", "current_development_version", mode="before"
    )
    @classmethod
    def validate_version_fields(cls, v: object) -> ModelSemVer | None:
        """Validate and convert version fields to ModelSemVer."""
        if v is None:
            return None
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, dict):
            return ModelSemVer(**v)
        if isinstance(v, str):
            from omnibase_core.models.primitives.model_semver import (
                parse_semver_from_string,
            )

            return parse_semver_from_string(v)
        msg = "Version field must be ModelSemVer, dict, or str"
        raise ModelOnexError(message=msg, error_code=EnumCoreErrorCode.VALIDATION_ERROR)

    @field_validator("versions")
    @classmethod
    def validate_versions_list(
        cls,
        v: list["ModelToolVersion"],
    ) -> list["ModelToolVersion"]:
        """Validate versions list consistency."""
        if not v:
            msg = "versions list cannot be empty"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        # Check for duplicate versions
        version_strings = [str(version.version) for version in v]
        if len(version_strings) != len(set(version_strings)):
            msg = "Duplicate versions found in versions list"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return v

    @field_validator("max_memory_mb", "max_cpu_percent", "timeout_seconds")
    @classmethod
    def validate_positive_values(cls, v: int) -> int:
        """Validate positive integer values."""
        if v <= 0:
            msg = "Value must be positive"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("testing")
    @classmethod
    def validate_testing_config(cls, v: "ModelToolTesting") -> "ModelToolTesting":
        """Validate testing configuration."""
        if v.minimum_coverage_percentage < 0 or v.minimum_coverage_percentage > 100:
            msg = "Coverage percentage must be between 0 and 100"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    def get_version_by_string(self, version_string: str) -> "ModelToolVersion | None":
        """Get version by version string."""
        for version in self.versions:
            if str(version.version) == version_string:
                return version
        return None

    def get_versions_by_status(
        self,
        status: "EnumVersionStatus",
    ) -> list["ModelToolVersion"]:
        """Get all versions with specified status."""
        return [version for version in self.versions if version.status == status]

    def get_active_versions(self) -> list["ModelToolVersion"]:
        """Get all active versions."""
        return self.get_versions_by_status("ACTIVE")

    def get_capability_by_name(
        self,
        capability_name: str,
    ) -> "ModelToolCapability | None":
        """Get capability by name."""
        for capability in self.capabilities:
            if capability.name == capability_name:
                return capability
        return None

    def is_security_compliant(self) -> bool:
        """Check if tool meets security requirements."""
        return (
            self.security.security_profile_required
            in ["SP0_BOOTSTRAP", "SP1_BASELINE", "SP2_PRODUCTION", "SP3_HIGH_ASSURANCE"]
            and len(self.security.external_endpoints) == 0
        ) or self.security.requires_network_access

    def get_recommended_version(self) -> "ModelToolVersion | None":
        """Get the recommended version."""
        for version in self.versions:
            if version.recommended and version.status == "ACTIVE":
                return version
        return None

    def get_total_dependencies(self) -> int:
        """Get total number of dependencies."""
        return len(self.dependencies)

    def get_optional_dependencies(self) -> int:
        """Get number of optional dependencies."""
        return sum(1 for dep in self.dependencies if dep.optional)

    def get_required_dependencies(self) -> int:
        """Get number of required dependencies."""
        return self.get_total_dependencies() - self.get_optional_dependencies()

    def get_resource_summary(self) -> TypedDictToolResourceSummary:
        """Get resource requirements summary."""
        return TypedDictToolResourceSummary(
            max_memory_mb=self.max_memory_mb,
            max_cpu_percent=self.max_cpu_percent,
            timeout_seconds=self.timeout_seconds,
            execution_mode=self.execution_mode,
            requires_network=self.security.requires_network_access,
            requires_separate_port=self.integration.requires_separate_port,
        )

    def get_comprehensive_summary(self) -> TypedDictToolComprehensiveSummary:
        """Get comprehensive tool summary."""
        return TypedDictToolComprehensiveSummary(
            tool_name=self.tool_name,
            description=self.description,
            author=self.author,
            node_type=self.node_type.value,
            business_logic_pattern=self.business_logic_pattern.value,
            status=self.status.value,
            current_stable_version=self.current_stable_version,
            current_development_version=self.current_development_version,
            version_count=len(self.versions),
            active_version_count=len(self.get_active_versions()),
            capability_count=len(self.capabilities),
            dependency_count=self.get_total_dependencies(),
            required_dependencies=self.get_required_dependencies(),
            optional_dependencies=self.get_optional_dependencies(),
            resource_requirements=self.get_resource_summary(),
            security_compliant=self.is_security_compliant(),
            recommended_version=self.get_recommended_version(),
            security_assessment=self.security.get_security_assessment(),
            testing_requirements=self.testing.get_test_requirement_summary(),
        )


# Forward Reference Resolution
# ============================
# This module uses TYPE_CHECKING imports to break circular dependencies with
# 10+ external models (ModelToolVersion, ModelToolCapability, ModelToolDependency,
# ModelToolIntegration, ModelToolSecurity, ModelToolTesting) and 4 enums
# (EnumNodeType, EnumBusinessLogicPattern, EnumToolStatus, EnumVersionStatus).
#
# WHY EXPLICIT IMPORTS ARE REQUIRED (vs TYPE_CHECKING-only):
# ----------------------------------------------------------
# 1. TYPE_CHECKING imports are ONLY available during static type analysis
#    (mypy, pyright) - they do NOT exist at runtime.
#
# 2. Pydantic's model_rebuild() runs at RUNTIME and needs the actual types
#    to resolve string annotations like "ModelToolVersion" into real classes.
#
# 3. For SELF-REFERENTIAL forward refs (e.g., ModelActionCategory referencing
#    itself), no extra imports are needed - the class is already defined.
#
# 4. For CROSS-MODULE forward refs (like this file), we MUST import the types
#    at runtime before calling model_rebuild() so Pydantic can find them.
#
# Pattern:
#   - TYPE_CHECKING block: Static analysis sees proper types
#   - Runtime imports below: Injects types for model_rebuild() resolution
#   - try/except: Handles circular imports during module initialization
#
# See also: model_schema_property.py for a similar well-documented pattern.
try:
    # Runtime imports inject types into namespace for model_rebuild() resolution.
    # These MUST be imported at runtime (not just under TYPE_CHECKING) because
    # Pydantic's model_rebuild() needs to resolve the string annotations.
    from omnibase_core.enums.enum_business_logic_pattern import EnumBusinessLogicPattern
    from omnibase_core.enums.enum_node_type import EnumNodeType
    from omnibase_core.enums.enum_tool_status import EnumToolStatus
    from omnibase_core.enums.enum_version_status import EnumVersionStatus
    from omnibase_core.models.core.model_tool_capability import ModelToolCapability
    from omnibase_core.models.core.model_tool_dependency import ModelToolDependency
    from omnibase_core.models.core.model_tool_integration import ModelToolIntegration
    from omnibase_core.models.core.model_tool_security import ModelToolSecurity
    from omnibase_core.models.core.model_tool_testing import ModelToolTesting
    from omnibase_core.models.core.model_tool_version import ModelToolVersion

    ModelToolManifest.model_rebuild()
except Exception:  # catch-all-ok: circular import protection during model rebuild
    pass
