# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ONCP package builder service.

Assembles a ``.oncp`` content-addressed zip bundle from overlays, scenarios,
and invariants. The builder accumulates artefacts in memory and writes the
final bundle when :meth:`OncpBuilder.build` is called.

Determinism guarantee: identical inputs (same overlays in the same order,
same scenario/invariant content) produce identical manifest hashes.

MVP scope: local file export only. No distribution registry.

See Also:
    - OMN-2758: Phase 5 — .oncp contract package MVP
    - OMN-2754: ``compute_canonical_hash`` canonical hash utility
    - OMN-2757: Overlay stacking pipeline

.. versionadded:: 0.19.0
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import yaml

import omnibase_core
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.package.model_oncp_invariant_entry import ModelOncpInvariantEntry
from omnibase_core.package.model_oncp_manifest import (
    MANIFEST_VERSION,
    ModelOncpManifest,
)
from omnibase_core.package.model_oncp_overlay_entry import ModelOncpOverlayEntry
from omnibase_core.package.model_oncp_scenario_entry import ModelOncpScenarioEntry
from omnibase_core.utils.util_canonical_hash import compute_canonical_hash

__all__ = ["OncpBuilder"]

# Internal YAML sub-path constants.
_MANIFEST_PATH = "manifest.yaml"
_OVERLAYS_DIR = "overlays"
_SCENARIOS_DIR = "scenarios"
_INVARIANTS_DIR = "invariants"


def _hash_bytes(data: bytes) -> str:
    """Return a ``sha256:<hex>`` prefixed hash of *data*.

    Args:
        data: Raw bytes to hash.

    Returns:
        ``"sha256:<64-char-hex>"`` string.
    """
    import hashlib

    digest = hashlib.sha256(data).hexdigest()
    return f"sha256:{digest}"


class OncpBuilder:
    """Assembles a ``.oncp`` content-addressed zip bundle.

    Usage::

        builder = OncpBuilder(
            package_id="omninode.effects.http_fetch",
            package_version="1.2.0",
            base_profile_ref="effect_idempotent",
            base_profile_version="1.0.0",
        )
        builder.add_overlay(patch, scope=EnumOverlayScope.PROJECT, overlay_id="my_patch")
        builder.add_scenario(Path("/tmp/happy_path.yaml"))
        builder.add_invariants(Path("/tmp/core_invariants.yaml"))
        builder.build(Path("/tmp/my_effect.oncp"))

    The builder is single-use; calling :meth:`build` a second time produces
    an identical archive (determinism guarantee).

    Attributes:
        package_id: Reverse-dotted package identifier.
        package_version: SemVer string for the package release.
        base_profile_ref: Name of the base profile.
        base_profile_version: SemVer string of the base profile.

    .. versionadded:: 0.19.0
    """

    def __init__(
        self,
        *,
        package_id: str,
        package_version: str,
        base_profile_ref: str,
        base_profile_version: str,
        base_profile_hash: str | None = None,
    ) -> None:
        """Initialise the builder.

        Args:
            package_id: Reverse-dotted identifier for the package
                (e.g. ``"omninode.effects.http_fetch"``).
            package_version: SemVer string for the package release.
            base_profile_ref: Name of the base profile extended by overlays.
            base_profile_version: SemVer string of the base profile.
            base_profile_hash: Optional pre-computed content hash of the base
                profile. When ``None``, a placeholder is computed from the
                ``base_profile_ref`` and ``base_profile_version`` strings.
        """
        if not package_id.strip():
            raise ModelOnexError(
                "package_id must not be empty",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            )
        if not package_version.strip():
            raise ModelOnexError(
                "package_version must not be empty",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            )
        if not base_profile_ref.strip():
            raise ModelOnexError(
                "base_profile_ref must not be empty",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            )
        if not base_profile_version.strip():
            raise ModelOnexError(
                "base_profile_version must not be empty",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            )

        self.package_id = package_id
        self.package_version = package_version
        self.base_profile_ref = base_profile_ref
        self.base_profile_version = base_profile_version

        # Use provided hash or derive a deterministic placeholder from refs.
        self._base_profile_hash: str = base_profile_hash or (
            "sha256:"
            + compute_canonical_hash(
                {
                    "profile": base_profile_ref,
                    "version": base_profile_version,
                }
            )
        )

        # Accumulated artefacts — stored in (entry, raw_bytes) pairs.
        self._overlays: list[tuple[ModelOncpOverlayEntry, bytes]] = []
        self._scenarios: list[tuple[ModelOncpScenarioEntry, bytes]] = []
        self._invariants: list[tuple[ModelOncpInvariantEntry, bytes]] = []

    # =========================================================================
    # Artefact accumulation
    # =========================================================================

    def add_overlay(
        self,
        patch: ModelContractPatch,
        *,
        scope: EnumOverlayScope,
        overlay_id: str,
    ) -> OncpBuilder:
        """Add an overlay patch to the bundle.

        Patches are applied in the order they are added (``order_index``
        is assigned sequentially starting from 0).

        Args:
            patch: The :class:`ModelContractPatch` to bundle.
            scope: Precedence tier for the overlay.
            overlay_id: Stable identifier for the overlay.

        Returns:
            ``self`` for method chaining.

        Raises:
            ModelOnexError: If ``overlay_id`` is empty.
        """
        if not overlay_id.strip():
            raise ModelOnexError(
                "overlay_id must not be empty",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            )

        order_index = len(self._overlays)
        safe_id = overlay_id.replace("/", "_").replace(".", "_")
        path_in_zip = f"{_OVERLAYS_DIR}/{safe_id}.overlay.yaml"

        # Serialise via canonical Pydantic dump → YAML for the zip entry.
        raw_dict = patch.model_dump(mode="json", exclude_none=True)
        raw_bytes = yaml.dump(raw_dict, sort_keys=True, allow_unicode=True).encode(
            "utf-8"
        )
        content_hash = _hash_bytes(raw_bytes)

        entry = ModelOncpOverlayEntry(
            overlay_id=overlay_id,
            scope=scope,
            path=path_in_zip,
            content_hash=content_hash,
            order_index=order_index,
        )
        self._overlays.append((entry, raw_bytes))
        return self

    def add_scenario(
        self,
        scenario_path: Path,
        *,
        scenario_id: str | None = None,
        required: bool = True,
    ) -> OncpBuilder:
        """Add a scenario file to the bundle.

        Args:
            scenario_path: Path to the scenario YAML file on disk.
            scenario_id: Explicit identifier; defaults to the file stem.
            required: Whether the scenario must pass.

        Returns:
            ``self`` for method chaining.

        Raises:
            ModelOnexError: If ``scenario_path`` does not exist.
        """
        if not scenario_path.exists():
            raise ModelOnexError(
                f"Scenario file not found: {scenario_path}",
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            )

        raw_bytes = scenario_path.read_bytes()
        sid = scenario_id or scenario_path.stem
        path_in_zip = f"{_SCENARIOS_DIR}/{scenario_path.name}"
        content_hash = _hash_bytes(raw_bytes)

        entry = ModelOncpScenarioEntry(
            id=sid,
            path=path_in_zip,
            content_hash=content_hash,
            required=required,
        )
        self._scenarios.append((entry, raw_bytes))
        return self

    def add_invariants(
        self,
        invariants_path: Path,
        *,
        invariants_id: str | None = None,
        required: bool = True,
    ) -> OncpBuilder:
        """Add an invariants file to the bundle.

        Args:
            invariants_path: Path to the invariants YAML file on disk.
            invariants_id: Explicit identifier; defaults to the file stem.
            required: Whether the invariant suite must pass.

        Returns:
            ``self`` for method chaining.

        Raises:
            ModelOnexError: If ``invariants_path`` does not exist.
        """
        if not invariants_path.exists():
            raise ModelOnexError(
                f"Invariants file not found: {invariants_path}",
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            )

        raw_bytes = invariants_path.read_bytes()
        iid = invariants_id or invariants_path.stem
        path_in_zip = f"{_INVARIANTS_DIR}/{invariants_path.name}"
        content_hash = _hash_bytes(raw_bytes)

        entry = ModelOncpInvariantEntry(
            id=iid,
            path=path_in_zip,
            content_hash=content_hash,
            required=required,
        )
        self._invariants.append((entry, raw_bytes))
        return self

    # =========================================================================
    # Build
    # =========================================================================

    def build(self, output_path: Path) -> ModelOncpManifest:
        """Assemble and write the ``.oncp`` zip bundle.

        Computes the resolved contract hash from the stacked overlay hashes
        (in application order), writes all artefacts into the zip, and
        serialises the manifest as ``manifest.yaml`` at the root.

        The operation is deterministic: identical inputs produce identical
        output bytes.

        Args:
            output_path: Destination path for the ``.oncp`` file.

        Returns:
            The :class:`ModelOncpManifest` that was embedded in the zip.

        Raises:
            OSError: If the output path is not writable.
        """
        # Build resolved_contract_hash by hashing all overlay content_hashes
        # (in application order) together with the base profile hash.
        resolved_hash_input: dict[str, object] = {
            "base_profile_hash": self._base_profile_hash,
            "overlays": [entry.content_hash for entry, _ in self._overlays],
        }
        resolved_contract_hash = "sha256:" + compute_canonical_hash(resolved_hash_input)

        overlay_entries = [entry for entry, _ in self._overlays]
        scenario_entries = [entry for entry, _ in self._scenarios]
        invariant_entries = [entry for entry, _ in self._invariants]

        manifest = ModelOncpManifest(
            manifest_version=MANIFEST_VERSION,
            package_id=self.package_id,
            package_version=self.package_version,
            base_profile_ref=self.base_profile_ref,
            base_profile_version=self.base_profile_version,
            base_profile_hash=self._base_profile_hash,
            omnibase_core_version=omnibase_core.__version__,
            overlays=overlay_entries,
            resolved_contract_hash=resolved_contract_hash,
            scenarios=scenario_entries,
            invariants=invariant_entries,
        )

        # Serialise manifest to YAML bytes.
        manifest_dict = manifest.model_dump(mode="json", exclude_none=True)
        manifest_bytes = yaml.dump(
            manifest_dict, sort_keys=True, allow_unicode=True
        ).encode("utf-8")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(
            output_path, mode="w", compression=zipfile.ZIP_STORED
        ) as zf:
            zf.writestr(_MANIFEST_PATH, manifest_bytes)

            for overlay_entry, overlay_bytes in self._overlays:
                zf.writestr(overlay_entry.path, overlay_bytes)

            for scenario_entry, scenario_bytes in self._scenarios:
                zf.writestr(scenario_entry.path, scenario_bytes)

            for invariant_entry, invariant_bytes in self._invariants:
                zf.writestr(invariant_entry.path, invariant_bytes)

        return manifest

    def build_bytes(self) -> tuple[bytes, ModelOncpManifest]:
        """Build the ``.oncp`` bundle in memory and return raw bytes.

        Useful for testing or in-process transfer without touching the
        filesystem.

        Returns:
            A tuple of ``(zip_bytes, manifest)``.
        """
        # Build resolved_contract_hash.
        resolved_hash_input: dict[str, object] = {
            "base_profile_hash": self._base_profile_hash,
            "overlays": [entry.content_hash for entry, _ in self._overlays],
        }
        resolved_contract_hash = "sha256:" + compute_canonical_hash(resolved_hash_input)

        overlay_entries = [entry for entry, _ in self._overlays]
        scenario_entries = [entry for entry, _ in self._scenarios]
        invariant_entries = [entry for entry, _ in self._invariants]

        manifest = ModelOncpManifest(
            manifest_version=MANIFEST_VERSION,
            package_id=self.package_id,
            package_version=self.package_version,
            base_profile_ref=self.base_profile_ref,
            base_profile_version=self.base_profile_version,
            base_profile_hash=self._base_profile_hash,
            omnibase_core_version=omnibase_core.__version__,
            overlays=overlay_entries,
            resolved_contract_hash=resolved_contract_hash,
            scenarios=scenario_entries,
            invariants=invariant_entries,
        )

        manifest_dict = manifest.model_dump(mode="json", exclude_none=True)
        manifest_bytes = yaml.dump(
            manifest_dict, sort_keys=True, allow_unicode=True
        ).encode("utf-8")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr(_MANIFEST_PATH, manifest_bytes)

            for overlay_entry, overlay_bytes in self._overlays:
                zf.writestr(overlay_entry.path, overlay_bytes)

            for scenario_entry, scenario_bytes in self._scenarios:
                zf.writestr(scenario_entry.path, scenario_bytes)

            for invariant_entry, invariant_bytes in self._invariants:
                zf.writestr(invariant_entry.path, invariant_bytes)

        return buf.getvalue(), manifest
