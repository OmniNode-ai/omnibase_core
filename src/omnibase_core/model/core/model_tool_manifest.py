"""
Tool Manifest Model - Tier 2 Metadata

Pydantic model for tool-level metadata in the three-tier metadata system.
Represents individual tools within a group with version management and capabilities.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from omnibase_core.model.core.model_semver import ModelSemVer, SemVerField


class EnumToolStatus(str, Enum):
    """Tool lifecycle status values."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    MAINTENANCE = "maintenance"
    END_OF_LIFE = "end_of_life"


class EnumVersionStatus(str, Enum):
    """Version lifecycle status values."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BETA = "beta"
    ALPHA = "alpha"
    END_OF_LIFE = "end_of_life"


class EnumNodeType(str, Enum):
    """ONEX node type classifications."""

    COMPUTE = "COMPUTE"
    EFFECT = "EFFECT"
    ORCHESTRATOR = "ORCHESTRATOR"
    REDUCER = "REDUCER"
    HUB = "HUB"


class EnumBusinessLogicPattern(str, Enum):
    """Business logic pattern classifications."""

    STATELESS = "stateless"
    STATEFUL = "stateful"
    COORDINATION = "coordination"
    AGGREGATION = "aggregation"


class ModelToolVersion(BaseModel):
    """Version information for a tool."""

    version: SemVerField = Field(description="Semantic version identifier")
    status: EnumVersionStatus = Field(description="Version lifecycle status")
    release_date: datetime = Field(description="Version release date")
    breaking_changes: bool = Field(
        description="Whether version contains breaking changes",
    )
    recommended: bool = Field(description="Whether version is recommended for use")
    deprecation_date: datetime | None = Field(
        default=None,
        description="Date when version was deprecated",
    )
    end_of_life_date: datetime | None = Field(
        default=None,
        description="Date when version reaches end of life",
    )
    changelog: str | None = Field(
        default=None,
        description="Version changelog summary",
    )


class ModelToolDependency(BaseModel):
    """Tool-specific dependency definition."""

    name: str = Field(description="Dependency name")
    type: str = Field(description="Dependency type (service, protocol, library)")
    target: str = Field(description="Dependency target (URL, protocol name, etc.)")
    binding: str = Field(
        description="How dependency is bound (injection, lookup, etc.)",
    )
    optional: bool = Field(default=False, description="Whether dependency is optional")
    description: str = Field(description="Dependency purpose and usage")
    version_requirement: str | None = Field(
        default=None,
        description="Version requirement specification",
    )


class ModelToolCapability(BaseModel):
    """Tool capability definition."""

    name: str = Field(description="Capability name")
    description: str = Field(description="Capability description")
    input_types: list[str] = Field(
        default_factory=list,
        description="Input data types supported",
    )
    output_types: list[str] = Field(
        default_factory=list,
        description="Output data types produced",
    )
    operations: list[str] = Field(
        default_factory=list,
        description="Operations provided by capability",
    )


class ModelToolIntegration(BaseModel):
    """Service integration configuration for tool."""

    auto_load_strategy: str = Field(
        default="current_stable",
        description="Strategy for loading tool versions",
    )
    fallback_versions: list[str] = Field(
        default_factory=list,
        description="Fallback versions if preferred unavailable",
    )
    version_directory_pattern: str = Field(
        default="v{major}_{minor}_{patch}",
        description="Directory pattern for versions",
    )
    implementation_file: str = Field(
        default="node.py",
        description="Main implementation file name",
    )
    contract_file: str = Field(
        default="contract.yaml",
        description="Contract file name",
    )
    main_class_name: str = Field(description="Main implementation class name")
    load_as_module: bool = Field(
        default=True,
        description="Whether loaded as module by service",
    )
    requires_separate_port: bool = Field(
        default=False,
        description="Whether tool requires separate HTTP port",
    )
    initialization_order: int = Field(
        default=5,
        description="Initialization order relative to other tools",
    )
    shutdown_timeout: int = Field(
        default=30,
        description="Graceful shutdown timeout in seconds",
    )
    health_check_via_service: bool = Field(
        default=True,
        description="Whether health checked by parent service",
    )


class ModelToolTesting(BaseModel):
    """Testing requirements and configuration."""

    required_ci_tiers: list[str] = Field(
        default_factory=lambda: ["unit", "integration"],
        description="Required CI testing tiers",
    )
    minimum_coverage_percentage: float = Field(
        default=85.0,
        description="Minimum test coverage percentage required",
    )
    canonical_test_case_ids: list[str] = Field(
        default_factory=list,
        description="Canonical test case identifiers",
    )
    performance_test_required: bool = Field(
        default=False,
        description="Whether performance testing is required",
    )
    security_test_required: bool = Field(
        default=True,
        description="Whether security testing is required",
    )


class ModelToolSecurity(BaseModel):
    """Security configuration and requirements."""

    processes_sensitive_data: bool = Field(
        default=False,
        description="Whether tool processes sensitive data",
    )
    data_classification: str = Field(
        default="internal",
        description="Data classification level",
    )
    requires_network_access: bool = Field(
        default=False,
        description="Whether tool requires network access",
    )
    external_endpoints: list[str] = Field(
        default_factory=list,
        description="External endpoints accessed",
    )
    security_profile_required: str = Field(
        default="SP0_BOOTSTRAP",
        description="Required security profile level",
    )


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
    created_date: datetime = Field(description="Tool creation timestamp")
    last_modified_date: datetime = Field(description="Last modification timestamp")

    # === TOOL CLASSIFICATION ===
    node_type: EnumNodeType = Field(description="ONEX node type classification")
    business_logic_pattern: EnumBusinessLogicPattern = Field(
        description="Business logic pattern classification",
    )
    meta_type: str = Field(default="tool", description="Meta-type classification")
    runtime_language_hint: str = Field(
        default="python>=3.11",
        description="Runtime language requirement",
    )

    # === TOOL STATUS ===
    status: EnumToolStatus = Field(description="Current tool lifecycle status")
    lifecycle: str = Field(default="active", description="Tool lifecycle state")

    # === VERSION CATALOG ===
    current_stable_version: SemVerField = Field(
        description="Current stable version identifier",
    )
    current_development_version: SemVerField | None = Field(
        default=None,
        description="Current development version identifier",
    )
    versions: list[ModelToolVersion] = Field(
        description="Available versions with lifecycle information",
    )

    # === CAPABILITIES ===
    capabilities: list[ModelToolCapability] = Field(
        description="Tool capabilities and operations",
    )
    protocols_supported: list[str] = Field(
        default_factory=list,
        description="Supported protocol interfaces",
    )

    # === DEPENDENCIES ===
    dependencies: list[ModelToolDependency] = Field(
        default_factory=list,
        description="Tool-specific dependencies",
    )

    # === SERVICE INTEGRATION ===
    integration: ModelToolIntegration = Field(
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
    testing: ModelToolTesting = Field(
        description="Testing requirements and configuration",
    )

    # === SECURITY CONFIGURATION ===
    security: ModelToolSecurity = Field(
        description="Security requirements and configuration",
    )

    # === METADATA VALIDATION ===
    schema_version: SemVerField = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
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

    class Config:
        """Pydantic configuration."""

        frozen = True
        use_enum_values = True

    @field_validator("versions")
    @classmethod
    def validate_versions_list(
        cls,
        v: list[ModelToolVersion],
    ) -> list[ModelToolVersion]:
        """Validate versions list consistency."""
        if not v:
            msg = "versions list cannot be empty"
            raise ValueError(msg)

        # Check for duplicate versions
        version_strings = [str(version.version) for version in v]
        if len(version_strings) != len(set(version_strings)):
            msg = "Duplicate versions found in versions list"
            raise ValueError(msg)

        return v

    @field_validator("max_memory_mb", "max_cpu_percent", "timeout_seconds")
    @classmethod
    def validate_positive_values(cls, v: int) -> int:
        """Validate positive integer values."""
        if v <= 0:
            msg = "Value must be positive"
            raise ValueError(msg)
        return v

    @field_validator("testing")
    @classmethod
    def validate_testing_config(cls, v: ModelToolTesting) -> ModelToolTesting:
        """Validate testing configuration."""
        if v.minimum_coverage_percentage < 0 or v.minimum_coverage_percentage > 100:
            msg = "Coverage percentage must be between 0 and 100"
            raise ValueError(msg)
        return v

    def get_version_by_string(self, version_string: str) -> ModelToolVersion | None:
        """Get version by version string."""
        for version in self.versions:
            if str(version.version) == version_string:
                return version
        return None

    def get_versions_by_status(
        self,
        status: EnumVersionStatus,
    ) -> list[ModelToolVersion]:
        """Get all versions with specified status."""
        return [version for version in self.versions if version.status == status]

    def get_active_versions(self) -> list[ModelToolVersion]:
        """Get all active versions."""
        return self.get_versions_by_status(EnumVersionStatus.ACTIVE)

    def get_capability_by_name(
        self,
        capability_name: str,
    ) -> ModelToolCapability | None:
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

    def get_recommended_version(self) -> ModelToolVersion | None:
        """Get the recommended version."""
        for version in self.versions:
            if version.recommended and version.status == EnumVersionStatus.ACTIVE:
                return version
        return None
