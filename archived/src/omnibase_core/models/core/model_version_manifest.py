"""
Version Manifest Model - Tier 3 Metadata

Pydantic model for version-level metadata in the three-tier metadata system.
Represents specific version implementations with contract compliance and validation.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from omnibase_core.models.core.model_semver import ModelSemVer, SemVerField


class EnumVersionStatus(str, Enum):
    """Version lifecycle status values."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BETA = "beta"
    ALPHA = "alpha"
    END_OF_LIFE = "end_of_life"


class EnumContractCompliance(str, Enum):
    """Contract compliance levels."""

    FULLY_COMPLIANT = "fully_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    VALIDATION_PENDING = "validation_pending"


class ModelVersionFile(BaseModel):
    """File reference within a version implementation."""

    file_path: str = Field(description="Relative path to file within version directory")
    file_type: str = Field(
        description="File type (contract, model, protocol, test, etc.)",
    )
    required: bool = Field(default=True, description="Whether file is required")
    description: str = Field(description="File purpose and contents")
    checksum: str | None = Field(
        default=None,
        description="File checksum for integrity verification",
    )


class ModelVersionContract(BaseModel):
    """Contract file information and validation status."""

    contract_file: str = Field(
        default="contract.yaml",
        description="Contract file name",
    )
    contract_version: SemVerField = Field(description="Contract version")
    contract_name: str = Field(description="Contract identifier")
    m1_compliant: bool = Field(
        default=True,
        description="Whether contract follows M1 standards",
    )
    validation_status: EnumContractCompliance = Field(
        description="Contract validation status",
    )
    validation_date: datetime | None = Field(
        default=None,
        description="Date when contract was validated",
    )
    validation_errors: list[str] = Field(
        default_factory=list,
        description="Contract validation errors",
    )


class ModelVersionImplementation(BaseModel):
    """Implementation file information."""

    implementation_file: str = Field(
        default="node.py",
        description="Main implementation file name",
    )
    main_class_name: str = Field(description="Main implementation class name")
    entry_point: str | None = Field(
        default=None,
        description="Entry point for standalone execution",
    )
    namespace: str = Field(description="Python namespace for the implementation")

    # File references
    model_files: list[ModelVersionFile] = Field(
        default_factory=list,
        description="Pydantic model files",
    )
    protocol_files: list[ModelVersionFile] = Field(
        default_factory=list,
        description="Protocol interface files",
    )
    enum_files: list[ModelVersionFile] = Field(
        default_factory=list,
        description="Enumeration definition files",
    )
    contract_files: list[ModelVersionFile] = Field(
        default_factory=list,
        description="Subcontract files",
    )


class ModelVersionTesting(BaseModel):
    """Version-specific testing information."""

    test_files: list[ModelVersionFile] = Field(
        default_factory=list,
        description="Test implementation files",
    )
    test_coverage_percentage: float | None = Field(
        default=None,
        description="Actual test coverage percentage",
    )
    test_results: dict[str, str] = Field(
        default_factory=dict,
        description="Test execution results by test type",
    )
    performance_benchmarks: dict[str, float] = Field(
        default_factory=dict,
        description="Performance benchmark results",
    )
    last_test_date: datetime | None = Field(
        default=None,
        description="Date when tests were last executed",
    )


class ModelVersionDeployment(BaseModel):
    """Deployment-specific configuration."""

    docker_image: str | None = Field(
        default=None,
        description="Docker image reference if containerized",
    )
    resource_requirements: dict[str, str] = Field(
        default_factory=dict,
        description="Resource requirements for deployment",
    )
    environment_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Required environment variables",
    )
    port_mappings: dict[str, int] = Field(
        default_factory=dict,
        description="Port mapping requirements",
    )
    health_check_endpoint: str = Field(
        default="/health",
        description="Health check endpoint path",
    )
    startup_timeout: int = Field(default=30, description="Startup timeout in seconds")


class ModelVersionSecurity(BaseModel):
    """Version-specific security configuration."""

    security_context: dict[str, str] = Field(
        default_factory=dict,
        description="Security context requirements",
    )
    data_handling_declaration: dict[str, str] = Field(
        default_factory=dict,
        description="Data handling and classification",
    )
    audit_events: list[str] = Field(
        default_factory=list,
        description="Security audit events generated",
    )
    encryption_requirements: dict[str, str] = Field(
        default_factory=dict,
        description="Encryption requirements",
    )
    authentication_methods: list[str] = Field(
        default_factory=list,
        description="Supported authentication methods",
    )


class ModelVersionDocumentation(BaseModel):
    """Version documentation information."""

    documentation_files: list[ModelVersionFile] = Field(
        default_factory=list,
        description="Documentation files",
    )
    readme_file: str | None = Field(
        default="README.md",
        description="README file name",
    )
    api_documentation: str | None = Field(
        default=None,
        description="API documentation file or URL",
    )
    changelog_entry: str | None = Field(
        default=None,
        description="Changelog entry for this version",
    )
    migration_guide: str | None = Field(
        default=None,
        description="Migration guide from previous versions",
    )


class ModelVersionManifest(BaseModel):
    """
    Tier 3: Version-level metadata model.

    Defines version-specific implementation details, contract compliance,
    testing status, and deployment configuration.
    """

    # === VERSION IDENTITY ===
    version: SemVerField = Field(description="Semantic version identifier")
    status: EnumVersionStatus = Field(description="Version lifecycle status")
    release_date: datetime = Field(description="Version release date")
    created_by: str = Field(
        default="ONEX Framework Team",
        description="Version creator",
    )

    # === VERSION METADATA ===
    breaking_changes: bool = Field(
        default=False,
        description="Whether version contains breaking changes",
    )
    recommended: bool = Field(
        default=True,
        description="Whether version is recommended for use",
    )
    deprecation_date: datetime | None = Field(
        default=None,
        description="Date when version was deprecated",
    )
    end_of_life_date: datetime | None = Field(
        default=None,
        description="Date when version reaches end of life",
    )

    # === CONTRACT COMPLIANCE ===
    contract: ModelVersionContract = Field(
        description="Contract file information and validation status",
    )

    # === IMPLEMENTATION DETAILS ===
    implementation: ModelVersionImplementation = Field(
        description="Implementation files and entry points",
    )

    # === TESTING INFORMATION ===
    testing: ModelVersionTesting = Field(description="Testing status and results")

    # === DEPLOYMENT CONFIGURATION ===
    deployment: ModelVersionDeployment = Field(
        description="Deployment requirements and configuration",
    )

    # === SECURITY CONFIGURATION ===
    security: ModelVersionSecurity = Field(
        description="Security requirements and configuration",
    )

    # === DOCUMENTATION ===
    documentation: ModelVersionDocumentation = Field(
        description="Documentation files and references",
    )

    # === VALIDATION METADATA ===
    schema_version: SemVerField = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Version manifest schema version",
    )
    checksum: str | None = Field(
        default=None,
        description="Version content checksum",
    )
    validation_date: datetime | None = Field(
        default=None,
        description="Date when version was validated",
    )

    # === BLUEPRINT COMPLIANCE ===
    blueprint_version: SemVerField = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Tool group blueprint version followed",
    )
    blueprint_compliant: bool = Field(
        default=True,
        description="Whether version follows blueprint standards",
    )

    class Config:
        """Pydantic configuration."""

        frozen = True
        use_enum_values = True

    @field_validator("deployment")
    @classmethod
    def validate_deployment_config(
        cls,
        v: ModelVersionDeployment,
    ) -> ModelVersionDeployment:
        """Validate deployment configuration."""
        if v.startup_timeout <= 0:
            msg = "startup_timeout must be positive"
            raise ValueError(msg)
        return v

    @field_validator("testing")
    @classmethod
    def validate_testing_config(cls, v: ModelVersionTesting) -> ModelVersionTesting:
        """Validate testing configuration."""
        if v.test_coverage_percentage is not None:
            if v.test_coverage_percentage < 0 or v.test_coverage_percentage > 100:
                msg = "test_coverage_percentage must be between 0 and 100"
                raise ValueError(msg)
        return v

    def is_current_stable(self) -> bool:
        """Check if this is a current stable version."""
        return (
            self.status == EnumVersionStatus.ACTIVE
            and self.recommended
            and not self.breaking_changes
        )

    def has_deprecation_status(self) -> bool:
        """Check if version has deprecation status."""
        return self.status == EnumVersionStatus.DEPRECATED or (
            self.deprecation_date is not None
            and self.deprecation_date <= datetime.now()
        )

    def is_end_of_life(self) -> bool:
        """Check if version has reached end of life."""
        return self.status == EnumVersionStatus.END_OF_LIFE or (
            self.end_of_life_date is not None
            and self.end_of_life_date <= datetime.now()
        )

    def is_contract_compliant(self) -> bool:
        """Check if version is fully contract compliant."""
        return (
            self.contract.validation_status == EnumContractCompliance.FULLY_COMPLIANT
            and self.contract.m1_compliant
            and len(self.contract.validation_errors) == 0
        )

    def is_production_ready(self) -> bool:
        """Check if version is ready for production deployment."""
        return (
            self.is_current_stable()
            and self.is_contract_compliant()
            and self.blueprint_compliant
            and self.testing.test_coverage_percentage is not None
            and self.testing.test_coverage_percentage >= 85.0
        )

    def get_file_by_type(self, file_type: str) -> list[ModelVersionFile]:
        """Get all files of specified type."""
        all_files = (
            self.implementation.model_files
            + self.implementation.protocol_files
            + self.implementation.enum_files
            + self.implementation.contract_files
            + self.testing.test_files
            + self.documentation.documentation_files
        )
        return [f for f in all_files if f.file_type == file_type]

    def get_required_files(self) -> list[ModelVersionFile]:
        """Get all required files."""
        all_files = (
            self.implementation.model_files
            + self.implementation.protocol_files
            + self.implementation.enum_files
            + self.implementation.contract_files
            + self.testing.test_files
            + self.documentation.documentation_files
        )
        return [f for f in all_files if f.required]

    def validate_file_integrity(self) -> dict[str, bool]:
        """Validate file integrity using checksums."""
        results = {}
        for file_group in [
            self.implementation.model_files,
            self.implementation.protocol_files,
            self.implementation.enum_files,
            self.implementation.contract_files,
            self.testing.test_files,
            self.documentation.documentation_files,
        ]:
            for file_ref in file_group:
                if file_ref.checksum:
                    # In a real implementation, this would verify file checksums
                    results[file_ref.file_path] = True
                else:
                    results[file_ref.file_path] = False
        return results
