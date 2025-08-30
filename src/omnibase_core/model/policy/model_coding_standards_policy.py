"""Pydantic model for ONEX Coding Standards Policy.

This model provides type-safe access to coding standards configuration
and ensures standards validation and compliance checking.
"""

from typing import Dict, List, Literal, Optional

import semver
from pydantic import BaseModel, Field, validator


class ModelNamingConvention(BaseModel):
    """Model for file and class naming convention rules."""

    pattern: str
    class_pattern: str
    example: str


class ModelNamingConventions(BaseModel):
    """Model for all naming convention rules."""

    model_files: ModelNamingConvention
    tool_files: ModelNamingConvention
    utility_files: ModelNamingConvention
    service_files: ModelNamingConvention
    node_files: ModelNamingConvention


class ModelTypeSafety(BaseModel):
    """Model for type safety requirements."""

    prohibited_types: List[str]
    required_patterns: Dict[str, str]
    type_checking: Dict[str, bool]


class ModelModelStandards(BaseModel):
    """Model for Pydantic model standards."""

    base_requirements: Dict[str, bool]
    field_naming: Dict[str, bool]
    validation_rules: Dict[str, str]


class ModelArchitecturePatterns(BaseModel):
    """Model for architecture pattern requirements."""

    protocol_resolution: Dict[str, bool]
    registry_injection: Dict[str, str]
    error_handling: Dict[str, str]


class ModelDocumentation(BaseModel):
    """Model for documentation standards."""

    docstring_format: str
    required_sections: List[str]
    class_documentation: Dict[str, bool]
    function_documentation: Dict[str, bool]


class ModelTestingStandards(BaseModel):
    """Model for testing requirements."""

    test_coverage: Dict[str, int]
    test_structure: Dict[str, bool]
    test_categories: Dict[str, str]


class ModelQualityStandards(BaseModel):
    """Model for code quality rules."""

    complexity_limits: Dict[str, int]
    code_style: Dict[str, str]
    maintainability: Dict[str, bool]


class ModelSecurityRequirements(BaseModel):
    """Model for security standards."""

    no_hardcoded_secrets: bool
    input_validation: str
    output_sanitization: str
    error_information_disclosure: str


class ModelPerformanceStandards(BaseModel):
    """Model for performance guidelines."""

    async_patterns: str
    lazy_loading: str
    caching_strategies: str
    resource_management: str


class ModelDependencyManagement(BaseModel):
    """Model for import and dependency rules."""

    import_organization: List[str]
    circular_imports: str
    relative_imports: str
    unused_imports: str
    dependency_rules: Dict[str, bool]


class ModelAgentDevelopment(BaseModel):
    """Model for agent-specific guidelines."""

    agent_structure: Dict[str, bool]
    agent_coordination: Dict[str, bool]
    agent_quality: Dict[str, bool]


class ModelCodingPrinciples(BaseModel):
    """Model for core coding principles."""

    strong_typing: bool = True
    no_any_usage: bool = True
    pydantic_models: bool = True
    protocol_resolution: bool = True
    registry_injection: bool = True
    camelcase_models: bool = True
    snake_case_files: bool = True
    one_model_per_file: bool = True


class ModelMaintenance(BaseModel):
    """Model for policy maintenance configuration."""

    review_schedule: str
    update_process: str
    version_control: bool
    backward_compatibility: str
    stakeholders: List[str]

    @validator("backward_compatibility")
    def validate_semver(cls, v):
        """Validate that backward_compatibility follows semantic versioning."""
        try:
            semver.VersionInfo.parse(v)
            return v
        except ValueError:
            raise ValueError(f"backward_compatibility must be valid semver: {v}")


class ModelCodingStandardsPolicy(BaseModel):
    """Complete model for ONEX Coding Standards Policy."""

    version: str = Field(
        ..., description="Policy version following semantic versioning"
    )
    schema_version: str = Field(
        ..., description="Schema version following semantic versioning"
    )

    principles: ModelCodingPrinciples
    naming_conventions: ModelNamingConventions
    type_safety: ModelTypeSafety
    model_standards: ModelModelStandards
    architecture_patterns: ModelArchitecturePatterns
    documentation: ModelDocumentation
    testing_standards: ModelTestingStandards
    quality_standards: ModelQualityStandards
    security_requirements: ModelSecurityRequirements
    performance_standards: ModelPerformanceStandards
    dependency_management: ModelDependencyManagement
    agent_development: ModelAgentDevelopment
    maintenance: ModelMaintenance

    @validator("version", "schema_version")
    def validate_semver_versions(cls, v):
        """Validate that versions follow semantic versioning."""
        try:
            semver.VersionInfo.parse(v)
            return v
        except ValueError:
            raise ValueError(f"Version must be valid semver: {v}")

    @validator("type_safety")
    def validate_prohibited_types(cls, v):
        """Ensure critical prohibited types are included."""
        required_prohibited = ["Any", "Dict[str, Any]", "List[Any]"]
        missing = [t for t in required_prohibited if t not in v.prohibited_types]
        if missing:
            raise ValueError(f"Missing required prohibited types: {missing}")
        return v

    def is_type_prohibited(self, type_string: str) -> bool:
        """Check if a type usage is prohibited."""
        return type_string in self.type_safety.prohibited_types

    def get_naming_pattern(self, file_type: str) -> Optional[ModelNamingConvention]:
        """Get naming convention for a specific file type."""
        type_mapping = {
            "model": self.naming_conventions.model_files,
            "tool": self.naming_conventions.tool_files,
            "utility": self.naming_conventions.utility_files,
            "service": self.naming_conventions.service_files,
            "node": self.naming_conventions.node_files,
        }
        return type_mapping.get(file_type)

    def validate_file_naming(self, filename: str, file_type: str) -> bool:
        """Validate that a filename follows naming conventions."""
        pattern = self.get_naming_pattern(file_type)
        if not pattern:
            return True  # No specific pattern defined

        # Simple pattern matching - would need regex for complex patterns
        if file_type == "model":
            return filename.startswith("model_") and filename.endswith(".py")
        elif file_type == "tool":
            return filename.startswith("tool_") and filename.endswith(".py")
        elif file_type == "utility":
            return filename.startswith("utility_") and filename.endswith(".py")
        elif file_type == "service":
            return filename.endswith("_service.py")
        elif file_type == "node":
            return filename.startswith("node_") and filename.endswith(".py")

        return True

    def get_complexity_limit(self, metric: str) -> Optional[int]:
        """Get complexity limit for a specific metric."""
        return self.quality_standards.complexity_limits.get(metric)

    def is_compatible_with_version(self, other_version: str) -> bool:
        """Check if this policy version is compatible with another version."""
        try:
            current = semver.VersionInfo.parse(self.version)
            other = semver.VersionInfo.parse(other_version)
            backward_compat = semver.VersionInfo.parse(
                self.maintenance.backward_compatibility
            )

            # Compatible if other version is within backward compatibility range
            return other >= backward_compat and other.major == current.major
        except ValueError:
            return False


class ModelCodingStandardsPolicyWrapper(BaseModel):
    """Wrapper model that matches the YAML structure."""

    coding_standards_policy: ModelCodingStandardsPolicy
