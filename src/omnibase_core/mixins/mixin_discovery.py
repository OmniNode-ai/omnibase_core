"""
Mixin Discovery API.

Provides programmatic discovery and querying of available mixins with metadata,
compatibility checking, and dependency resolution for intelligent composition.
"""

from pathlib import Path
from typing import cast

import yaml
from pydantic import TypeAdapter, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import VALIDATION_ERRORS
from omnibase_core.models.discovery.model_mixin_info import ModelMixinInfo
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

# Discovery constants
MAX_METADATA_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB limit for metadata files


class MixinDiscovery:
    """
    Discover and query available mixins.

    Provides intelligent mixin discovery, compatibility checking, and dependency
    resolution to support composition of ONEX nodes.

    Example:
        >>> discovery = MixinDiscovery()
        >>> mixins = discovery.get_all_mixins()
        >>> cache_mixins = discovery.get_mixins_by_category("caching")
        >>> compatible = discovery.find_compatible_mixins(["MixinEventBus"])
    """

    def __init__(self, mixins_path: Path | None = None) -> None:
        """
        Initialize mixin discovery system.

        Args:
            mixins_path: Optional custom path to mixins directory.
                        Defaults to src/omnibase_core/mixins.
        """
        self.mixins_path = mixins_path or (Path(__file__).parent.parent / "mixins")
        self.metadata_path = self.mixins_path / "mixin_metadata.yaml"
        self._mixins_cache: dict[str, ModelMixinInfo] | None = None

    @staticmethod
    def from_yaml_metadata(yaml_content: str) -> SerializedDict:
        """
        Parse YAML metadata content and validate structure with Pydantic.

        This method uses yaml.safe_load() followed by Pydantic validation
        to ensure type safety and proper structure validation.

        Args:
            yaml_content: Raw YAML content as string

        Returns:
            Validated metadata dictionary

        Raises:
            ModelOnexError: If YAML parsing or validation fails
        """
        try:
            # Parse YAML to Python objects
            raw_data = yaml.safe_load(yaml_content)

            # Validate structure using Pydantic TypeAdapter
            metadata_adapter = TypeAdapter(SerializedDict)
            return metadata_adapter.validate_python(raw_data)

        except yaml.YAMLError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Failed to parse mixin metadata YAML: {e}",
            ) from e
        except ValidationError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid metadata format: expected dictionary, got {type(raw_data).__name__}",
            ) from e

    def _load_metadata(self) -> dict[str, dict[str, object]]:
        """
        Load mixin metadata from YAML file.

        Returns:
            Dictionary mapping mixin keys to metadata dictionaries.

        Raises:
            OnexError: If metadata file is missing, too large, or invalid.
        """
        if not self.metadata_path.exists():
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
                message=(
                    f"Mixin metadata file not found: {self.metadata_path}. "
                    "Run metadata generation or create mixin_metadata.yaml manually."
                ),
            )

        # Check file size before loading
        try:
            file_size = self.metadata_path.stat().st_size
            if file_size > MAX_METADATA_FILE_SIZE_BYTES:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=(
                        f"Metadata file too large: {file_size} bytes exceeds "
                        f"{MAX_METADATA_FILE_SIZE_BYTES} byte limit"
                    ),
                )
        except OSError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                message=f"Failed to access mixin metadata file: {e}",
            ) from e

        try:
            with open(self.metadata_path, encoding="utf-8") as f:
                yaml_content = f.read()

            # Parse and validate YAML using Pydantic
            data = self.from_yaml_metadata(yaml_content)
            # Cast to dict[str, dict[str, object]] since YAML metadata structure
            # has mixin names as keys and their config dicts as values
            return cast(dict[str, dict[str, object]], data)

        except UnicodeDecodeError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                message=f"Metadata file encoding error: {e}",
            ) from e
        except PermissionError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                message=f"Permission denied reading metadata file: {e}",
            ) from e
        except OSError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                message=f"Failed to read mixin metadata file: {e}",
            ) from e

    def _build_mixin_cache(self) -> dict[str, ModelMixinInfo]:
        """
        Build internal cache of ModelMixinInfo objects from metadata.

        Returns:
            Dictionary mapping mixin names to ModelMixinInfo objects.

        Raises:
            OnexError: If metadata is invalid or parsing fails.
        """
        metadata = self._load_metadata()
        cache: dict[str, ModelMixinInfo] = {}

        for mixin_key, mixin_data in metadata.items():
            try:
                # Ensure name field is present
                if "name" not in mixin_data:
                    mixin_data["name"] = mixin_key

                # mixin_data is dict[str, object] which is valid for model_validate
                mixin_info = ModelMixinInfo.model_validate(mixin_data)
                cache[mixin_info.name] = mixin_info

            except VALIDATION_ERRORS as e:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Failed to parse metadata for mixin '{mixin_key}': {e}",
                ) from e

        return cache

    def reload(self) -> None:
        """
        Force reload of mixin metadata from disk.

        Clears the cache and forces re-reading of the metadata file on next access.
        Use this when the metadata file has been updated externally.

        Example:
            >>> discovery = MixinDiscovery()
            >>> mixins = discovery.get_all_mixins()  # Loads and caches
            >>> # ... metadata file updated externally ...
            >>> discovery.reload()  # Clear cache
            >>> mixins = discovery.get_all_mixins()  # Reloads from disk
        """
        self._mixins_cache = None

    def get_all_mixins(self) -> list[ModelMixinInfo]:
        """
        Get all available mixins with metadata.

        Results are cached after first load. Call reload() to force refresh.

        Returns:
            List of ModelMixinInfo objects for all available mixins.

        Example:
            >>> discovery = MixinDiscovery()
            >>> all_mixins = discovery.get_all_mixins()
            >>> print(f"Found {len(all_mixins)} mixins")
            >>> for mixin in all_mixins:
            ...     print(f"  - {mixin.name}: {mixin.description}")
        """
        if self._mixins_cache is None:
            self._mixins_cache = self._build_mixin_cache()

        return list(self._mixins_cache.values())

    def get_mixins_by_category(self, category: str) -> list[ModelMixinInfo]:
        """
        Get mixins filtered by category.

        Args:
            category: Category name to filter by (e.g., 'communication', 'caching').

        Returns:
            List of ModelMixinInfo objects matching the category.

        Example:
            >>> discovery = MixinDiscovery()
            >>> cache_mixins = discovery.get_mixins_by_category("caching")
            >>> print(f"Found {len(cache_mixins)} caching mixins")
        """
        all_mixins = self.get_all_mixins()
        return [m for m in all_mixins if m.category == category]

    def find_compatible_mixins(self, base_mixins: list[str]) -> list[ModelMixinInfo]:
        """
        Find mixins compatible with given base mixins.

        Identifies mixins that can be safely composed with the provided base mixins,
        excluding any mixins that are incompatible with any of the base mixins.

        Args:
            base_mixins: List of mixin names already selected.

        Returns:
            List of ModelMixinInfo objects compatible with all base mixins.

        Example:
            >>> discovery = MixinDiscovery()
            >>> base = ["MixinEventBus", "MixinCaching"]
            >>> compatible = discovery.find_compatible_mixins(base)
            >>> print(f"Found {len(compatible)} compatible mixins")
        """
        all_mixins = self.get_all_mixins()
        base_set = set(base_mixins)
        compatible: list[ModelMixinInfo] = []

        for mixin in all_mixins:
            # Skip if already in base set
            if mixin.name in base_set:
                continue

            # Check if incompatible with any base mixin
            incompatible_set = set(mixin.incompatible_with)
            if base_set.intersection(incompatible_set):
                continue

            # Check if any base mixin lists this as incompatible
            is_blocked = False
            for base_name in base_mixins:
                base_mixin = self._get_mixin_by_name(base_name)
                if base_mixin and mixin.name in base_mixin.incompatible_with:
                    is_blocked = True
                    break

            if not is_blocked:
                compatible.append(mixin)

        return compatible

    def get_mixin_dependencies(self, mixin_name: str) -> list[str]:
        """
        Get transitive dependencies for a mixin.

        Resolves all direct and indirect dependencies required by the specified mixin,
        returning them in dependency order (dependencies before dependents).

        Args:
            mixin_name: Name of the mixin to get dependencies for.

        Returns:
            List of dependency package/module names in dependency order.

        Raises:
            OnexError: If mixin is not found or circular dependencies are detected.

        Example:
            >>> discovery = MixinDiscovery()
            >>> deps = discovery.get_mixin_dependencies("MixinEventBus")
            >>> print(f"MixinEventBus requires: {', '.join(deps)}")
        """
        mixin = self._get_mixin_by_name(mixin_name)
        if not mixin:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Mixin not found: {mixin_name}",
            )

        # Start with direct dependencies
        dependencies = list(mixin.requires)

        # Check for mixin dependencies (other mixins required)
        visited: set[str] = {mixin_name}
        to_process = list(mixin.requires)

        while to_process:
            dep = to_process.pop(0)

            # Skip if already processed
            if dep in visited:
                continue

            visited.add(dep)

            # Check if this dependency is another mixin
            dep_mixin = self._get_mixin_by_name(dep)
            if dep_mixin:
                # Add transitive dependencies
                for transitive_dep in dep_mixin.requires:
                    if transitive_dep not in visited:
                        to_process.append(transitive_dep)
                        if transitive_dep not in dependencies:
                            # Insert before current dependency
                            insert_idx = dependencies.index(dep)
                            dependencies.insert(insert_idx, transitive_dep)

        return dependencies

    def _get_mixin_by_name(self, name: str) -> ModelMixinInfo | None:
        """
        Get a ModelMixinInfo by name from cache.

        Args:
            name: Mixin name to lookup.

        Returns:
            ModelMixinInfo object if found, None otherwise.
        """
        if self._mixins_cache is None:
            self._mixins_cache = self._build_mixin_cache()

        return self._mixins_cache.get(name)

    def get_mixin(self, name: str) -> ModelMixinInfo:
        """
        Get a specific mixin by name.

        Args:
            name: Mixin name to retrieve.

        Returns:
            ModelMixinInfo object.

        Raises:
            OnexError: If mixin is not found.

        Example:
            >>> discovery = MixinDiscovery()
            >>> event_bus = discovery.get_mixin("MixinEventBus")
            >>> print(event_bus.description)
        """
        mixin = self._get_mixin_by_name(name)
        if not mixin:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Mixin not found: {name}",
            )
        return mixin

    def get_categories(self) -> list[str]:
        """
        Get all unique mixin categories.

        Returns:
            Sorted list of unique category names.

        Example:
            >>> discovery = MixinDiscovery()
            >>> categories = discovery.get_categories()
            >>> print(f"Available categories: {', '.join(categories)}")
        """
        all_mixins = self.get_all_mixins()
        categories = {m.category for m in all_mixins}
        return sorted(categories)

    def validate_composition(self, mixin_names: list[str]) -> tuple[bool, list[str]]:
        """
        Validate that a set of mixins can be composed together.

        Checks for incompatibilities and missing dependencies in a proposed
        mixin composition.

        Args:
            mixin_names: List of mixin names to validate.

        Returns:
            Tuple of (is_valid, error_messages).
            is_valid is True if composition is valid, False otherwise.
            error_messages contains human-readable validation errors.

        Example:
            >>> discovery = MixinDiscovery()
            >>> mixins = ["MixinEventBus", "MixinCaching", "MixinHealthCheck"]
            >>> is_valid, errors = discovery.validate_composition(mixins)
            >>> if not is_valid:
            ...     for error in errors:
            ...         print(f"Validation error: {error}")
        """
        errors: list[str] = []

        # Check all mixins exist
        for name in mixin_names:
            if not self._get_mixin_by_name(name):
                errors.append(f"Unknown mixin: {name}")

        if errors:
            return False, errors

        # Check for incompatibilities
        for i, name1 in enumerate(mixin_names):
            mixin1 = self._get_mixin_by_name(name1)
            if not mixin1:
                continue

            for name2 in mixin_names[i + 1 :]:
                # Check if name2 is in name1's incompatible list
                if name2 in mixin1.incompatible_with:
                    errors.append(
                        f"Incompatible mixins: {name1} and {name2} "
                        f"(declared by {name1})"
                    )

                # Check reverse
                mixin2 = self._get_mixin_by_name(name2)
                if mixin2 and name1 in mixin2.incompatible_with:
                    errors.append(
                        f"Incompatible mixins: {name1} and {name2} "
                        f"(declared by {name2})"
                    )

        return len(errors) == 0, errors
