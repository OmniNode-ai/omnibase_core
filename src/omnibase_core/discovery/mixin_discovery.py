"""
Mixin Discovery API for autonomous code generation.

Provides programmatic discovery and querying of available mixins with metadata,
compatibility checking, and dependency resolution for intelligent composition.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import CoreErrorCode, OnexError
from omnibase_core.models.metadata.model_semver import ModelSemVer

# Discovery constants
MAX_METADATA_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB limit for metadata files


class MixinInfo(BaseModel):
    """
    Metadata information for a single mixin.

    Provides comprehensive information about mixin capabilities, compatibility,
    dependencies, and usage for autonomous code generation systems.
    """

    model_config = {
        "extra": "ignore",
        "validate_assignment": True,
    }

    name: str = Field(
        ...,
        description="Mixin class name (e.g., 'MixinEventBus')",
        json_schema_extra={"example": "MixinEventBus"},
    )
    description: str = Field(
        ...,
        description="Human-readable description of mixin functionality",
        json_schema_extra={"example": "Event-driven communication capabilities"},
    )
    version: ModelSemVer = Field(
        ...,
        description="Semantic version of the mixin",
        json_schema_extra={"example": {"major": 1, "minor": 0, "patch": 0}},
    )
    category: str = Field(
        ...,
        description="Functional category (e.g., 'communication', 'caching')",
        json_schema_extra={"example": "communication"},
    )
    requires: list[str] = Field(
        default_factory=list,
        description="Required dependencies (packages, modules)",
        json_schema_extra={
            "example": ["omnibase_core.core.onex_container", "pydantic"]
        },
    )
    compatible_with: list[str] = Field(
        default_factory=list,
        description="List of mixins this is compatible with",
        json_schema_extra={"example": ["MixinCaching", "MixinHealthCheck"]},
    )
    incompatible_with: list[str] = Field(
        default_factory=list,
        description="List of mixins this is incompatible with",
        json_schema_extra={"example": ["MixinSynchronous"]},
    )
    config_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration schema for this mixin",
        json_schema_extra={
            "example": {
                "event_bus_type": {
                    "type": "string",
                    "enum": ["redis", "kafka", "memory"],
                    "default": "redis",
                }
            }
        },
    )
    usage_examples: list[str] = Field(
        default_factory=list,
        description="Usage examples and use cases",
        json_schema_extra={
            "example": [
                "Database adapters that need to publish events",
                "API clients that emit status updates",
            ]
        },
    )


class MixinDiscovery:
    """
    Discover and query available mixins for autonomous code generation.

    Provides intelligent mixin discovery, compatibility checking, and dependency
    resolution to support autonomous composition of ONEX nodes.

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
        self._mixins_cache: dict[str, MixinInfo] | None = None

    def _load_metadata(self) -> dict[str, dict[str, Any]]:
        """
        Load mixin metadata from YAML file.

        Returns:
            Dictionary mapping mixin keys to metadata dictionaries.

        Raises:
            OnexError: If metadata file is missing, too large, or invalid.
        """
        if not self.metadata_path.exists():
            raise OnexError(
                code=CoreErrorCode.FILE_NOT_FOUND,
                message=(
                    f"Mixin metadata file not found: {self.metadata_path}. "
                    "Run metadata generation or create mixin_metadata.yaml manually."
                ),
            )

        # Check file size before loading
        try:
            file_size = self.metadata_path.stat().st_size
            if file_size > MAX_METADATA_FILE_SIZE_BYTES:
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message=(
                        f"Metadata file too large: {file_size} bytes exceeds "
                        f"{MAX_METADATA_FILE_SIZE_BYTES} byte limit"
                    ),
                )
        except OSError as e:
            raise OnexError(
                code=CoreErrorCode.FILE_READ_ERROR,
                message=f"Failed to access mixin metadata file: {e}",
            ) from e

        try:
            with open(self.metadata_path, encoding="utf-8") as f:
                data = yaml.safe_load(
                    f
                )  # yaml-ok: Mixin discovery requires raw YAML parsing for flexible metadata loading

            if not isinstance(data, dict):
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Invalid metadata format in {self.metadata_path}: expected dictionary",
                )

            return data

        except yaml.YAMLError as e:
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Failed to parse mixin metadata YAML: {e}",
            ) from e
        except UnicodeDecodeError as e:
            raise OnexError(
                code=CoreErrorCode.FILE_READ_ERROR,
                message=f"Metadata file encoding error: {e}",
            ) from e
        except PermissionError as e:
            raise OnexError(
                code=CoreErrorCode.FILE_READ_ERROR,
                message=f"Permission denied reading metadata file: {e}",
            ) from e
        except OSError as e:
            raise OnexError(
                code=CoreErrorCode.FILE_READ_ERROR,
                message=f"Failed to read mixin metadata file: {e}",
            ) from e

    def _build_mixin_cache(self) -> dict[str, MixinInfo]:
        """
        Build internal cache of MixinInfo objects from metadata.

        Returns:
            Dictionary mapping mixin names to MixinInfo objects.

        Raises:
            OnexError: If metadata is invalid or parsing fails.
        """
        metadata = self._load_metadata()
        cache: dict[str, MixinInfo] = {}

        for mixin_key, mixin_data in metadata.items():
            try:
                # Ensure name field is present
                if "name" not in mixin_data:
                    mixin_data["name"] = mixin_key

                mixin_info = MixinInfo(**mixin_data)
                cache[mixin_info.name] = mixin_info

            except Exception as e:
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
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

    def get_all_mixins(self) -> list[MixinInfo]:
        """
        Get all available mixins with metadata.

        Results are cached after first load. Call reload() to force refresh.

        Returns:
            List of MixinInfo objects for all available mixins.

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

    def get_mixins_by_category(self, category: str) -> list[MixinInfo]:
        """
        Get mixins filtered by category.

        Args:
            category: Category name to filter by (e.g., 'communication', 'caching').

        Returns:
            List of MixinInfo objects matching the category.

        Example:
            >>> discovery = MixinDiscovery()
            >>> cache_mixins = discovery.get_mixins_by_category("caching")
            >>> print(f"Found {len(cache_mixins)} caching mixins")
        """
        all_mixins = self.get_all_mixins()
        return [m for m in all_mixins if m.category == category]

    def find_compatible_mixins(self, base_mixins: list[str]) -> list[MixinInfo]:
        """
        Find mixins compatible with given base mixins.

        Identifies mixins that can be safely composed with the provided base mixins,
        excluding any mixins that are incompatible with any of the base mixins.

        Args:
            base_mixins: List of mixin names already selected.

        Returns:
            List of MixinInfo objects compatible with all base mixins.

        Example:
            >>> discovery = MixinDiscovery()
            >>> base = ["MixinEventBus", "MixinCaching"]
            >>> compatible = discovery.find_compatible_mixins(base)
            >>> print(f"Found {len(compatible)} compatible mixins")
        """
        all_mixins = self.get_all_mixins()
        base_set = set(base_mixins)
        compatible: list[MixinInfo] = []

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
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
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

    def _get_mixin_by_name(self, name: str) -> MixinInfo | None:
        """
        Get a MixinInfo by name from cache.

        Args:
            name: Mixin name to lookup.

        Returns:
            MixinInfo object if found, None otherwise.
        """
        if self._mixins_cache is None:
            self._mixins_cache = self._build_mixin_cache()

        return self._mixins_cache.get(name)

    def get_mixin(self, name: str) -> MixinInfo:
        """
        Get a specific mixin by name.

        Args:
            name: Mixin name to retrieve.

        Returns:
            MixinInfo object.

        Raises:
            OnexError: If mixin is not found.

        Example:
            >>> discovery = MixinDiscovery()
            >>> event_bus = discovery.get_mixin("MixinEventBus")
            >>> print(event_bus.description)
        """
        mixin = self._get_mixin_by_name(name)
        if not mixin:
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
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
