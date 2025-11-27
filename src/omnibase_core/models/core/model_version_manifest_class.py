"""
Version Manifest Model - Tier 3 Metadata.

Pydantic model for version-level metadata in the three-tier metadata system.
Represents specific version implementations with contract compliance and validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_contract_compliance import EnumContractCompliance
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_version_status import EnumVersionStatus
from omnibase_core.models.core.model_version_contract import ModelVersionContract
from omnibase_core.models.core.model_version_deployment import ModelVersionDeployment
from omnibase_core.models.core.model_version_documentation import (
    ModelVersionDocumentation,
)
from omnibase_core.models.core.model_version_file import ModelVersionFile
from omnibase_core.models.core.model_version_implementation import (
    ModelVersionImplementation,
)
from omnibase_core.models.core.model_version_security import ModelVersionSecurity
from omnibase_core.models.core.model_version_testing import ModelVersionTesting
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import SemVerField


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
        ...,  # REQUIRED - specify in contract
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
        ...,  # REQUIRED - specify in contract
        description="Tool group blueprint version followed",
    )
    blueprint_compliant: bool = Field(
        default=True,
        description="Whether version follows blueprint standards",
    )

    @field_validator("deployment")
    @classmethod
    def validate_deployment_config(
        cls,
        v: ModelVersionDeployment,
    ) -> ModelVersionDeployment:
        """Validate deployment configuration."""
        if v.startup_timeout <= 0:
            msg = "startup_timeout must be positive"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("testing")
    @classmethod
    def validate_testing_config(cls, v: ModelVersionTesting) -> ModelVersionTesting:
        """Validate testing configuration."""
        if v.test_coverage_percentage is not None:
            if v.test_coverage_percentage < 0 or v.test_coverage_percentage > 100:
                msg = "test_coverage_percentage must be between 0 and 100"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )
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
