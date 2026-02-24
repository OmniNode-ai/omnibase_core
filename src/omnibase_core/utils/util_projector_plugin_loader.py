# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ProjectorPluginLoader — runtime contract version validation for projector contracts.

This module validates that loaded projector contract versions match the expected
schema versions supported by the current runtime. As projector contracts evolve,
runtime validation prevents schema drift issues where a newer contract format is
loaded by an older runtime that does not support all fields.

Schema Version Registry
-----------------------
The registry defines:
  - ``CURRENT_SCHEMA_VERSION``: The latest supported schema version (preferred for new contracts)
  - ``SUPPORTED_SCHEMA_VERSIONS``: All versions the current runtime fully supports
  - ``DEPRECATED_SCHEMA_VERSIONS``: Versions that still work but should be migrated away from

Validation Behavior
-------------------
- **Unsupported version**: raises :class:`~omnibase_core.models.errors.model_onex_error.ModelOnexError`
  with ``CONTRACT_VALIDATION_ERROR`` and a clear message listing supported versions.
- **Deprecated version**: logs a ``WARNING`` via structured logging but proceeds normally.
- **Current / other supported version**: proceeds silently.

Usage
-----
    >>> from omnibase_core.utils.util_projector_plugin_loader import UtilProjectorPluginLoader
    >>> loader = UtilProjectorPluginLoader()
    >>> contract = loader.load(contract_data)  # dict from YAML
    >>> loader.validate_version(contract)       # raises on unsupported, warns on deprecated

Or use the combined helper:

    >>> contract = loader.load_and_validate(contract_data)

.. versionadded:: 0.5.0
    Added as part of OMN-1342 — Add Contract Version Validation to ProjectorPluginLoader.
"""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)
from omnibase_core.models.projectors.model_projector_contract import (
    ModelProjectorContract,
)

# ---------------------------------------------------------------------------
# Schema Version Registry
# ---------------------------------------------------------------------------

#: The latest stable schema version.  New contracts should target this version.
CURRENT_SCHEMA_VERSION: ModelSemVer = ModelSemVer(major=1, minor=0, patch=0)

#: Deprecated versions that still load successfully but trigger a WARNING log.
#: Operators running contracts on these versions should migrate to CURRENT_SCHEMA_VERSION.
DEPRECATED_SCHEMA_VERSIONS: frozenset[ModelSemVer] = frozenset(
    # No deprecated versions in the initial release.  Populate as the schema evolves.
    # Example for future use:
    # ModelSemVer(major=0, minor=9, patch=0),
)

#: All versions the current runtime supports (includes current + deprecated).
SUPPORTED_SCHEMA_VERSIONS: frozenset[ModelSemVer] = frozenset(
    {CURRENT_SCHEMA_VERSION} | DEPRECATED_SCHEMA_VERSIONS
)

#: Human-readable version compatibility matrix for documentation and error messages.
VERSION_COMPATIBILITY_MATRIX: dict[str, str] = {
    "1.0.0": "current — full support",
    # "0.9.0": "deprecated — loads but migration recommended",  # example
}


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class UtilProjectorPluginLoader:
    """Load and validate projector contracts with runtime schema version checking.

    This loader wraps Pydantic model validation with an additional layer that
    enforces schema version compatibility at runtime.  The goal is to surface
    schema drift early — before a mismatched contract silently drops fields or
    causes incorrect behaviour.

    Attributes:
        supported_versions: Set of versions this loader instance accepts.
            Defaults to :data:`SUPPORTED_SCHEMA_VERSIONS`.
        deprecated_versions: Set of versions that trigger a deprecation warning.
            Defaults to :data:`DEPRECATED_SCHEMA_VERSIONS`.

    Examples:
        Load a contract from a dict (e.g., parsed from YAML):

        >>> loader = UtilProjectorPluginLoader()
        >>> data = {
        ...     "projector_kind": "materialized_view",
        ...     "projector_id": "my-projector",
        ...     "name": "My Projector",
        ...     "version": "1.0.0",
        ...     "aggregate_type": "node",
        ...     "consumed_events": ["node.created.v1"],
        ...     "projection_schema": {
        ...         "table": "nodes",
        ...         "primary_key": "node_id",
        ...         "columns": [
        ...             {"name": "node_id", "type": "UUID",
        ...              "source": "event.payload.node_id"}
        ...         ],
        ...     },
        ...     "behavior": {"mode": "upsert", "upsert_key": "node_id"},
        ... }
        >>> contract = loader.load_and_validate(data)
        >>> contract.version
        '1.0.0'

    Thread Safety:
        ``UtilProjectorPluginLoader`` is stateless after construction (the
        version sets are frozen).  Instances are safe for concurrent use from
        multiple threads.
    """

    def __init__(
        self,
        supported_versions: frozenset[ModelSemVer] | None = None,
        deprecated_versions: frozenset[ModelSemVer] | None = None,
    ) -> None:
        """Initialise the loader.

        Args:
            supported_versions: Override the global supported version set.
                When ``None`` (default), uses :data:`SUPPORTED_SCHEMA_VERSIONS`.
            deprecated_versions: Override the global deprecated version set.
                When ``None`` (default), uses :data:`DEPRECATED_SCHEMA_VERSIONS`.
        """
        self._supported: frozenset[ModelSemVer] = (
            supported_versions
            if supported_versions is not None
            else SUPPORTED_SCHEMA_VERSIONS
        )
        self._deprecated: frozenset[ModelSemVer] = (
            deprecated_versions
            if deprecated_versions is not None
            else DEPRECATED_SCHEMA_VERSIONS
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, data: dict[str, object]) -> ModelProjectorContract:
        """Parse *data* into a :class:`ModelProjectorContract`.

        Args:
            data: Raw dict representation of a projector contract (e.g., loaded
                from a YAML file via ``util_safe_yaml_loader``).

        Returns:
            Validated :class:`ModelProjectorContract` instance.

        Raises:
            ModelOnexError: If Pydantic validation fails.
        """
        try:
            return ModelProjectorContract.model_validate(data)
        except PydanticValidationError as exc:
            projector_id = data.get("projector_id", "<unknown>")
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                message=f"Projector contract validation failed: {exc}",
                context={"projector_id": projector_id},
            ) from exc

    def validate_version(self, contract: ModelProjectorContract) -> None:
        """Validate the contract schema version against the runtime registry.

        Args:
            contract: A fully-loaded :class:`ModelProjectorContract`.

        Raises:
            ModelOnexError: If the contract's ``version`` is not in
                :attr:`supported_versions`.  The error message lists all
                supported versions so operators know what to migrate to.

        Warns:
            Emits a structured ``WARNING`` log when the version is in
                :attr:`deprecated_versions` (supported but no longer recommended).
        """
        version_str = contract.version

        # Parse the version string — fail fast on malformed strings
        try:
            parsed: ModelSemVer = parse_semver_from_string(version_str)
        except ModelOnexError as exc:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                message=(
                    f"Projector contract '{contract.projector_id}' has an invalid "
                    f"version format '{version_str}': {exc}"
                ),
                context={
                    "projector_id": contract.projector_id,
                    "version": version_str,
                },
            ) from exc

        # Check support
        if parsed not in self._supported:
            supported_strs = sorted(str(v) for v in self._supported)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                message=(
                    f"Projector contract '{contract.projector_id}' uses unsupported "
                    f"schema version '{version_str}'.  "
                    f"Supported versions: {supported_strs}.  "
                    f"Update the contract to a supported version or upgrade the runtime."
                ),
                context={
                    "projector_id": contract.projector_id,
                    "contract_version": version_str,
                    "supported_versions": supported_strs,
                },
            )

        # Warn on deprecated
        if parsed in self._deprecated:
            emit_log_event(
                LogLevel.WARNING,
                (
                    f"Projector contract '{contract.projector_id}' uses deprecated "
                    f"schema version '{version_str}'.  "
                    f"Migrate to version '{CURRENT_SCHEMA_VERSION}' to silence this warning."
                ),
                context={
                    "projector_id": contract.projector_id,
                    "contract_version": version_str,
                    "current_version": str(CURRENT_SCHEMA_VERSION),
                    "ticket": "OMN-1342",
                },
            )

    def load_and_validate(self, data: dict[str, object]) -> ModelProjectorContract:
        """Parse *data* and validate the schema version in one call.

        This is the preferred entry point for production use.  It combines
        :meth:`load` and :meth:`validate_version` into a single operation.

        Args:
            data: Raw dict representation of a projector contract (e.g. from YAML).

        Returns:
            Validated :class:`ModelProjectorContract` instance.

        Raises:
            ModelOnexError: If parsing fails or the schema version is unsupported.
        """
        contract = self.load(data)
        self.validate_version(contract)
        return contract


__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "DEPRECATED_SCHEMA_VERSIONS",
    "SUPPORTED_SCHEMA_VERSIONS",
    "VERSION_COMPATIBILITY_MATRIX",
    "UtilProjectorPluginLoader",
]
