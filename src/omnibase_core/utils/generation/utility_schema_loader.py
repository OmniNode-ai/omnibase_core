"""
Schema Loader Utility for ONEX Contract Generation.

Handles loading and parsing of external schema files referenced by $ref.
Provides proper file resolution and YAML parsing.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from omnibase.enums.enum_log_level import LogLevelEnum

from omnibase_core.core.core_structured_logging import \
    emit_log_event_sync as emit_log_event


class UtilitySchemaLoader:
    """
    Utility for loading external schema files.

    Handles:
    - Resolving relative paths from contract location
    - Loading and parsing YAML schema files
    - Caching loaded schemas for performance
    - Error handling for missing/invalid schemas
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize the schema loader.

        Args:
            base_path: Base directory for resolving relative schema paths
        """
        self.base_path = base_path or Path.cwd()
        self._schema_cache: Dict[str, Dict[str, Any]] = {}

    def load_schema(
        self, schema_path: str, contract_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Load a schema file from the given path.

        Args:
            schema_path: Path to the schema file (relative or absolute)
            contract_dir: Directory containing the contract (for relative path resolution)

        Returns:
            Parsed schema as dictionary

        Raises:
            FileNotFoundError: If schema file doesn't exist
            yaml.YAMLError: If schema file is invalid YAML
        """
        # Use contract directory if provided, otherwise use base path
        base_dir = contract_dir or self.base_path

        # Resolve the full path
        if Path(schema_path).is_absolute():
            full_path = Path(schema_path)
        else:
            full_path = base_dir / schema_path

        # Normalize path for caching
        cache_key = str(full_path.resolve())

        # Check cache first
        if cache_key in self._schema_cache:
            emit_log_event(
                LogLevelEnum.DEBUG,
                f"Loading schema from cache: {schema_path}",
                {"schema_path": schema_path, "full_path": str(full_path)},
            )
            return self._schema_cache[cache_key]

        emit_log_event(
            LogLevelEnum.INFO,
            f"Loading external schema: {schema_path}",
            {"schema_path": schema_path, "full_path": str(full_path)},
        )

        try:
            # Check if file exists
            if not full_path.exists():
                raise FileNotFoundError(f"Schema file not found: {full_path}")

            # Load and parse YAML
            with open(full_path, "r", encoding="utf-8") as f:
                schema_data = yaml.safe_load(f)

            if not isinstance(schema_data, dict):
                raise ValueError(f"Schema file must contain a YAML object: {full_path}")

            # Cache the loaded schema
            self._schema_cache[cache_key] = schema_data

            emit_log_event(
                LogLevelEnum.DEBUG,
                f"Successfully loaded schema: {schema_path}",
                {
                    "schema_path": schema_path,
                    "properties_count": len(schema_data.get("properties", {})),
                    "has_required": "required" in schema_data,
                    "schema_type": schema_data.get("type", "unknown"),
                },
            )

            return schema_data

        except FileNotFoundError:
            emit_log_event(
                LogLevelEnum.ERROR,
                f"Schema file not found: {schema_path}",
                {"schema_path": schema_path, "full_path": str(full_path)},
            )
            raise

        except yaml.YAMLError as e:
            emit_log_event(
                LogLevelEnum.ERROR,
                f"Invalid YAML in schema file: {schema_path}",
                {"schema_path": schema_path, "yaml_error": str(e)},
            )
            raise

        except Exception as e:
            emit_log_event(
                LogLevelEnum.ERROR,
                f"Error loading schema file: {schema_path}",
                {
                    "schema_path": schema_path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def resolve_schema_path(self, ref_path: str, contract_dir: Path) -> Path:
        """
        Resolve a schema reference path to an absolute path.

        Args:
            ref_path: Reference path from $ref (e.g., 'omnibase/schemas/core/semver.yaml')
            contract_dir: Directory containing the contract file

        Returns:
            Resolved absolute path to schema file
        """
        # Handle different path patterns
        if ref_path.startswith("/"):
            # Absolute path
            return Path(ref_path)
        elif ref_path.startswith("omnibase/"):
            # ONEX-relative path - resolve from project root
            # Find the omnibase root by looking for src/omnibase
            current = contract_dir.resolve()
            while current.parent != current:
                if (current / "src" / "omnibase").exists():
                    return current / "src" / ref_path
                current = current.parent
            # Fallback to relative resolution
            return contract_dir / ref_path
        else:
            # Relative path
            return contract_dir / ref_path

    def extract_schema_fragment(
        self, schema_data: Dict[str, Any], fragment: str
    ) -> Dict[str, Any]:
        """
        Extract a specific fragment from a schema using JSON Pointer syntax.

        Args:
            schema_data: Full schema data
            fragment: JSON Pointer fragment (e.g., '#/', '#/definitions/User')

        Returns:
            Extracted schema fragment
        """
        if not fragment or fragment == "#/" or fragment == "#":
            # Return the root schema
            return schema_data

        if fragment.startswith("#/"):
            # JSON Pointer - split and navigate
            parts = fragment[2:].split("/")  # Remove '#/' prefix
            current = schema_data

            for part in parts:
                if not part:  # Handle empty parts from double slashes
                    continue

                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    raise KeyError(f"Schema fragment not found: {fragment}")

            return current
        else:
            raise ValueError(f"Invalid schema fragment syntax: {fragment}")

    def clear_cache(self):
        """Clear the schema cache."""
        self._schema_cache.clear()
        emit_log_event(LogLevelEnum.DEBUG, "Schema cache cleared", {})
