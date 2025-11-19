"""Pydantic models for mixin metadata validation and discovery.

This module provides structured models for validating and working with
mixin metadata defined in mixin_metadata.yaml. It enables type-safe
mixin discovery, validation, and code generation.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.models.errors.model_onex_error import ModelOnexError


# =============================================================================
# Version Model
# =============================================================================


class ModelMixinVersion(BaseModel):
    """Semantic version for mixin metadata.

    Attributes:
        major: Major version number (breaking changes)
        minor: Minor version number (new features)
        patch: Patch version number (bug fixes)
    """

    major: int = Field(..., ge=0, description="Major version number")
    minor: int = Field(..., ge=0, description="Minor version number")
    patch: int = Field(..., ge=0, description="Patch version number")

    def __str__(self) -> str:
        """Return semantic version string."""
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def from_string(cls, version_str: str) -> "ModelMixinVersion":
        """Parse version string like '1.0.0' into ModelMixinVersion.

        Args:
            version_str: Version string in format 'major.minor.patch'

        Returns:
            Parsed version model

        Raises:
            ModelOnexError: If version string is invalid
        """
        try:
            parts = version_str.split(".")
            if len(parts) != 3:
                raise ValueError(f"Invalid version format: {version_str}")
            return cls(major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2]))
        except (ValueError, IndexError) as e:
            raise ModelOnexError(f"Invalid version string '{version_str}': {e}") from e


# =============================================================================
# Configuration Schema Models
# =============================================================================


class ModelMixinConfigField(BaseModel):
    """Configuration field definition in mixin metadata.

    Attributes:
        type: Field type (string, integer, float, boolean, array, object)
        default: Default value for the field
        description: Human-readable field description
        minimum: Minimum value (for numeric types)
        maximum: Maximum value (for numeric types)
        enum: Allowed values (for enum types)
        items: Item schema (for array types)
    """

    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., description="Field type")
    default: Any = Field(None, description="Default value")
    description: str = Field("", description="Field description")
    minimum: float | int | None = Field(None, description="Minimum value")
    maximum: float | int | None = Field(None, description="Maximum value")
    enum: list[str] | None = Field(None, description="Allowed enum values")
    items: dict[str, Any] | None = Field(None, description="Array item schema")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate field type is supported."""
        valid_types = {
            "string",
            "integer",
            "float",
            "number",
            "boolean",
            "array",
            "object",
        }
        if v not in valid_types:
            raise ValueError(f"Invalid field type '{v}'. Must be one of {valid_types}")
        return v


# =============================================================================
# Code Pattern Models
# =============================================================================


class ModelMixinMethodParameter(BaseModel):
    """Method parameter definition.

    Attributes:
        name: Parameter name
        type: Parameter type annotation
        default: Default value (if optional)
        description: Parameter description
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type annotation")
    default: Any = Field(None, description="Default value")
    description: str = Field("", description="Parameter description")


class ModelMixinMethod(BaseModel):
    """Method definition in code patterns.

    Attributes:
        name: Method name
        signature: Full method signature
        description: Method description
        example: Usage example code
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Method name")
    signature: str = Field(..., description="Full method signature")
    description: str = Field("", description="Method description")
    example: str = Field("", description="Usage example code")


class ModelMixinProperty(BaseModel):
    """Property definition in code patterns.

    Attributes:
        name: Property name
        type: Property type annotation
        description: Property description
    """

    name: str = Field(..., description="Property name")
    type: str = Field(..., description="Property type annotation")
    description: str = Field("", description="Property description")


class ModelMixinCodePatterns(BaseModel):
    """Code generation patterns for mixin.

    Attributes:
        inheritance: Inheritance pattern
        initialization: Initialization code
        methods: Method definitions
        properties: Property definitions
    """

    model_config = ConfigDict(extra="forbid")

    inheritance: str = Field("", description="Inheritance pattern")
    initialization: str = Field("", description="Initialization code")
    methods: list[ModelMixinMethod] = Field(default_factory=list, description="Methods")
    properties: list[ModelMixinProperty] = Field(
        default_factory=list, description="Properties"
    )


# =============================================================================
# Preset Configuration Models
# =============================================================================


class ModelMixinPreset(BaseModel):
    """Preset configuration for common use cases.

    Attributes:
        description: Preset description
        config: Configuration values
    """

    description: str = Field(..., description="Preset description")
    config: dict[str, Any] = Field(default_factory=dict, description="Config values")


# =============================================================================
# Performance Models
# =============================================================================


class ModelMixinPerformanceUseCase(BaseModel):
    """Performance data for specific use case.

    Attributes:
        use_case: Use case name
        recommended_config: Recommended preset name
        expected_overhead: Expected overhead description
    """

    use_case: str = Field(..., description="Use case name")
    recommended_config: str = Field(..., description="Recommended preset")
    expected_overhead: str = Field(..., description="Expected overhead")


class ModelMixinPerformance(BaseModel):
    """Performance characteristics and recommendations.

    Attributes:
        overhead_per_call: Overhead per call description
        memory_per_instance: Memory per instance description
        recommended_max_retries: Recommended maximum retries (if applicable)
        typical_use_cases: Performance data per use case
    """

    overhead_per_call: str = Field("", description="Overhead per call")
    memory_per_instance: str = Field("", description="Memory per instance")
    recommended_max_retries: int | None = Field(None, description="Max retries")
    typical_use_cases: list[ModelMixinPerformanceUseCase] = Field(
        default_factory=list, description="Use case performance data"
    )


# =============================================================================
# Main Mixin Metadata Model
# =============================================================================


class ModelMixinMetadata(BaseModel):
    """Complete metadata for a single mixin.

    Attributes:
        name: Mixin class name
        description: Human-readable description
        version: Semantic version
        category: Mixin category (flow_control, observability, etc.)
        requires: Required dependencies (modules/packages)
        compatible_with: Compatible mixin names
        incompatible_with: Incompatible mixin names
        config_schema: Configuration field definitions
        usage_examples: Usage example descriptions
        presets: Preset configurations
        code_patterns: Code generation patterns
        implementation_notes: Implementation guidance
        performance: Performance characteristics
        documentation_url: Link to detailed documentation
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Mixin class name")
    description: str = Field(..., description="Mixin description")
    version: ModelMixinVersion = Field(..., description="Semantic version")
    category: str = Field(..., description="Mixin category")

    # Dependencies and compatibility
    requires: list[str] = Field(default_factory=list, description="Required imports")
    compatible_with: list[str] = Field(
        default_factory=list, description="Compatible mixins"
    )
    incompatible_with: list[str] = Field(
        default_factory=list, description="Incompatible mixins"
    )

    # Configuration
    config_schema: dict[str, ModelMixinConfigField] = Field(
        default_factory=dict, description="Configuration schema"
    )

    # Usage and examples
    usage_examples: list[str] = Field(
        default_factory=list, description="Usage examples"
    )
    presets: dict[str, ModelMixinPreset] = Field(
        default_factory=dict, description="Presets"
    )

    # Code generation
    code_patterns: ModelMixinCodePatterns | None = Field(
        None, description="Code patterns"
    )

    # Documentation
    implementation_notes: list[str] = Field(
        default_factory=list, description="Implementation notes"
    )
    performance: ModelMixinPerformance | None = Field(
        None, description="Performance info"
    )
    documentation_url: str | None = Field(None, description="Documentation URL")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category is one of the known categories."""
        valid_categories = {
            "flow_control",
            "observability",
            "security",
            "data_processing",
            "integration",
            "utility",
            "state_management",
            "communication",
        }
        if v not in valid_categories:
            # Allow unknown categories but could log a warning in production
            pass
        return v

    @model_validator(mode="after")
    def validate_compatibility(self) -> "ModelMixinMetadata":
        """Validate compatibility constraints are consistent."""
        # A mixin can't be both compatible and incompatible with the same mixin
        compatible_set = set(self.compatible_with)
        incompatible_set = set(self.incompatible_with)

        overlap = compatible_set & incompatible_set
        if overlap:
            raise ValueError(
                f"Mixin {self.name} has conflicting compatibility: "
                f"{overlap} listed in both compatible_with and incompatible_with"
            )

        return self


# =============================================================================
# Collection Model
# =============================================================================


class ModelMixinMetadataCollection(BaseModel):
    """Collection of all mixin metadata.

    Attributes:
        mixins: Dictionary mapping mixin key to metadata
    """

    mixins: dict[str, ModelMixinMetadata] = Field(
        default_factory=dict, description="Mixin metadata by key"
    )

    @classmethod
    def load_from_yaml(cls, yaml_path: Path | str) -> "ModelMixinMetadataCollection":
        """Load mixin metadata from YAML file.

        Args:
            yaml_path: Path to mixin_metadata.yaml

        Returns:
            Loaded metadata collection

        Raises:
            ModelOnexError: If YAML cannot be loaded or parsed
        """
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise ModelOnexError(f"Mixin metadata file not found: {yaml_path}")

        try:
            with yaml_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            raise ModelOnexError(f"Failed to load YAML from {yaml_path}: {e}") from e

        if not isinstance(data, dict):
            raise ModelOnexError(
                f"Expected dict at root of {yaml_path}, got {type(data)}"
            )

        mixins = {}
        for key, mixin_data in data.items():
            try:
                # Parse version - handle both dict and string formats
                version_data = mixin_data.get("version")
                if isinstance(version_data, dict):
                    version = ModelMixinVersion(**version_data)
                elif isinstance(version_data, str):
                    version = ModelMixinVersion.from_string(version_data)
                else:
                    # Default version if missing
                    version = ModelMixinVersion(major=1, minor=0, patch=0)

                # Parse config schema
                config_schema = {}
                if "config_schema" in mixin_data:
                    for field_name, field_data in mixin_data["config_schema"].items():
                        config_schema[field_name] = ModelMixinConfigField(**field_data)

                # Parse presets
                presets = {}
                if "presets" in mixin_data:
                    for preset_name, preset_data in mixin_data["presets"].items():
                        presets[preset_name] = ModelMixinPreset(**preset_data)

                # Parse code patterns
                code_patterns = None
                if "code_patterns" in mixin_data:
                    cp_data = mixin_data["code_patterns"]
                    methods = []
                    if "methods" in cp_data:
                        for method_data in cp_data["methods"]:
                            methods.append(ModelMixinMethod(**method_data))

                    properties = []
                    if "properties" in cp_data:
                        for prop_data in cp_data["properties"]:
                            properties.append(ModelMixinProperty(**prop_data))

                    code_patterns = ModelMixinCodePatterns(
                        inheritance=cp_data.get("inheritance", ""),
                        initialization=cp_data.get("initialization", ""),
                        methods=methods,
                        properties=properties,
                    )

                # Parse performance
                performance = None
                if "performance" in mixin_data:
                    perf_data = mixin_data["performance"]
                    use_cases = []
                    if "typical_use_cases" in perf_data:
                        for uc_data in perf_data["typical_use_cases"]:
                            use_cases.append(ModelMixinPerformanceUseCase(**uc_data))

                    performance = ModelMixinPerformance(
                        overhead_per_call=perf_data.get("overhead_per_call", ""),
                        memory_per_instance=perf_data.get("memory_per_instance", ""),
                        recommended_max_retries=perf_data.get(
                            "recommended_max_retries"
                        ),
                        typical_use_cases=use_cases,
                    )

                # Create metadata
                metadata = ModelMixinMetadata(
                    name=mixin_data.get("name", key),
                    description=mixin_data.get("description", ""),
                    version=version,
                    category=mixin_data.get("category", "utility"),
                    requires=mixin_data.get("requires", []),
                    compatible_with=mixin_data.get("compatible_with", []),
                    incompatible_with=mixin_data.get("incompatible_with", []),
                    config_schema=config_schema,
                    usage_examples=mixin_data.get("usage_examples", []),
                    presets=presets,
                    code_patterns=code_patterns,
                    implementation_notes=mixin_data.get("implementation_notes", []),
                    performance=performance,
                    documentation_url=mixin_data.get("documentation_url"),
                )

                mixins[key] = metadata

            except Exception as e:
                raise ModelOnexError(
                    f"Failed to parse mixin '{key}' from {yaml_path}: {e}"
                ) from e

        return cls(mixins=mixins)

    def get_mixin(self, name: str) -> ModelMixinMetadata | None:
        """Get mixin metadata by name.

        Args:
            name: Mixin key or class name

        Returns:
            Mixin metadata or None if not found
        """
        # Try by key first
        if name in self.mixins:
            return self.mixins[name]

        # Try by class name
        for mixin in self.mixins.values():
            if mixin.name == name:
                return mixin

        return None

    def get_mixins_by_category(self, category: str) -> list[ModelMixinMetadata]:
        """Get all mixins in a specific category.

        Args:
            category: Category name

        Returns:
            List of mixins in that category
        """
        return [m for m in self.mixins.values() if m.category == category]

    def validate_compatibility(self, mixin_names: list[str]) -> tuple[bool, list[str]]:
        """Check if a set of mixins are compatible with each other.

        Args:
            mixin_names: List of mixin names to check

        Returns:
            Tuple of (is_compatible, list_of_conflicts)
        """
        conflicts = []

        for i, name1 in enumerate(mixin_names):
            mixin1 = self.get_mixin(name1)
            if not mixin1:
                conflicts.append(f"Unknown mixin: {name1}")
                continue

            for name2 in mixin_names[i + 1 :]:
                mixin2 = self.get_mixin(name2)
                if not mixin2:
                    conflicts.append(f"Unknown mixin: {name2}")
                    continue

                # Check if explicitly incompatible
                if (
                    name2 in mixin1.incompatible_with
                    or name1 in mixin2.incompatible_with
                ):
                    conflicts.append(
                        f"Incompatible mixins: {mixin1.name} and {mixin2.name}"
                    )

        return (len(conflicts) == 0, conflicts)

    def get_all_categories(self) -> list[str]:
        """Get list of all unique categories.

        Returns:
            Sorted list of category names
        """
        categories = {m.category for m in self.mixins.values()}
        return sorted(categories)

    def get_mixin_count(self) -> int:
        """Get total number of mixins.

        Returns:
            Count of mixins
        """
        return len(self.mixins)
