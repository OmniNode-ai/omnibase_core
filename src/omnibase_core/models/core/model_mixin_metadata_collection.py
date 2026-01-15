"""Pydantic model for mixin metadata collection.

This module provides the ModelMixinMetadataCollection class for loading,
validating, and working with collections of mixin metadata from YAML files.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_mixin_code_patterns import ModelMixinCodePatterns
from omnibase_core.models.core.model_mixin_config_field import ModelMixinConfigField
from omnibase_core.models.core.model_mixin_metadata import ModelMixinMetadata
from omnibase_core.models.core.model_mixin_method import ModelMixinMethod
from omnibase_core.models.core.model_mixin_performance import ModelMixinPerformance
from omnibase_core.models.core.model_mixin_performance_use_case import (
    ModelMixinPerformanceUseCase,
)
from omnibase_core.models.core.model_mixin_preset import ModelMixinPreset
from omnibase_core.models.core.model_mixin_property import ModelMixinProperty
from omnibase_core.models.core.model_mixin_version import ModelMixinVersion
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelMixinMetadataCollection(BaseModel):
    """Collection of all mixin metadata.

    Attributes:
        mixins: Dictionary mapping mixin key to metadata
    """

    mixins: dict[str, ModelMixinMetadata] = Field(
        default_factory=dict, description="Mixin metadata by key"
    )

    @classmethod
    def from_yaml(cls, yaml_path: Path | str) -> "ModelMixinMetadataCollection":
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
            raise ModelOnexError(
                message=f"Mixin metadata file not found: {yaml_path}",
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            )

        try:
            with yaml_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ModelOnexError(
                message=f"YAML parsing error in {yaml_path}: {e}",
                error_code=EnumCoreErrorCode.PARSING_ERROR,
            ) from e
        except OSError as e:
            raise ModelOnexError(
                message=f"Failed to read YAML file {yaml_path}: {e}",
                error_code=EnumCoreErrorCode.FILE_READ_ERROR,
            ) from e

        if not isinstance(data, dict):
            raise ModelOnexError(
                message=f"Expected dict at root of {yaml_path}, got {type(data)}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
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
                    cs_data = mixin_data["config_schema"] or {}
                    if not isinstance(cs_data, dict):
                        raise ModelOnexError(
                            message=f"config_schema for mixin '{key}' must be a mapping, got {type(cs_data).__name__}",
                            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        )
                    for field_name, field_data in cs_data.items():
                        config_schema[field_name] = ModelMixinConfigField(**field_data)

                # Parse presets
                presets = {}
                if "presets" in mixin_data:
                    presets_data = mixin_data["presets"] or {}
                    if not isinstance(presets_data, dict):
                        raise ModelOnexError(
                            message=f"presets for mixin '{key}' must be a mapping, got {type(presets_data).__name__}",
                            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        )
                    for preset_name, preset_data in presets_data.items():
                        presets[preset_name] = ModelMixinPreset(**preset_data)

                # Parse code patterns
                code_patterns = None
                if "code_patterns" in mixin_data:
                    cp_data = mixin_data["code_patterns"] or {}
                    if not isinstance(cp_data, dict):
                        raise ModelOnexError(
                            message=f"code_patterns for mixin '{key}' must be a mapping, got {type(cp_data).__name__}",
                            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        )

                    methods = []
                    if "methods" in cp_data:
                        methods_data = (
                            cp_data["methods"] if cp_data["methods"] is not None else []
                        )
                        if not isinstance(methods_data, list):
                            raise ModelOnexError(
                                message=f"code_patterns.methods for mixin '{key}' must be a list, got {type(methods_data).__name__}",
                                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                            )
                        for method_data in methods_data:
                            methods.append(ModelMixinMethod(**method_data))

                    properties = []
                    if "properties" in cp_data:
                        properties_data = (
                            cp_data["properties"]
                            if cp_data["properties"] is not None
                            else []
                        )
                        if not isinstance(properties_data, list):
                            raise ModelOnexError(
                                message=f"code_patterns.properties for mixin '{key}' must be a list, got {type(properties_data).__name__}",
                                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                            )
                        for prop_data in properties_data:
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
                    perf_data = mixin_data["performance"] or {}
                    if not isinstance(perf_data, dict):
                        raise ModelOnexError(
                            message=f"performance for mixin '{key}' must be a mapping, got {type(perf_data).__name__}",
                            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        )

                    use_cases = []
                    if "typical_use_cases" in perf_data:
                        use_cases_data = (
                            perf_data["typical_use_cases"]
                            if perf_data["typical_use_cases"] is not None
                            else []
                        )
                        if not isinstance(use_cases_data, list):
                            raise ModelOnexError(
                                message=f"performance.typical_use_cases for mixin '{key}' must be a list, got {type(use_cases_data).__name__}",
                                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                            )
                        for uc_data in use_cases_data:
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
                requires_val = mixin_data.get("requires")
                compatible_val = mixin_data.get("compatible_with")
                incompatible_val = mixin_data.get("incompatible_with")
                usage_val = mixin_data.get("usage_examples")
                impl_notes_val = mixin_data.get("implementation_notes")
                metadata = ModelMixinMetadata(
                    name=mixin_data.get("name", key),
                    description=mixin_data.get("description", ""),
                    version=version,
                    category=mixin_data.get("category", "utility"),
                    requires=requires_val if requires_val is not None else [],
                    compatible_with=compatible_val
                    if compatible_val is not None
                    else [],
                    incompatible_with=incompatible_val
                    if incompatible_val is not None
                    else [],
                    config_schema=config_schema,
                    usage_examples=usage_val if usage_val is not None else [],
                    presets=presets,
                    code_patterns=code_patterns,
                    implementation_notes=impl_notes_val
                    if impl_notes_val is not None
                    else [],
                    performance=performance,
                    documentation_url=mixin_data.get("documentation_url"),
                )

                mixins[key] = metadata

            except (AttributeError, KeyError, TypeError, ValueError) as e:
                raise ModelOnexError(
                    message=f"Failed to parse mixin '{key}' from {yaml_path}: {e}",
                    error_code=EnumCoreErrorCode.PARSING_ERROR,
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
