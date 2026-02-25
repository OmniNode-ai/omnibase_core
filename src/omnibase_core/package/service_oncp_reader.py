# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ONCP package reader service.

Reads and validates a ``.oncp`` content-addressed zip bundle. Provides
digest verification for all bundled artefacts and manifest integrity checks.

MVP scope: local file reading only. No distribution registry.

See Also:
    - OMN-2758: Phase 5 — .oncp contract package MVP
    - OMN-2754: ``compute_canonical_hash`` canonical hash utility
    - OMN-2757: Overlay stacking pipeline

.. versionadded:: 0.19.0
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.package.model_oncp_manifest import ModelOncpManifest
from omnibase_core.package.model_oncp_scenario_entry import ModelOncpScenarioEntry

__all__ = ["OncpReader"]

_MANIFEST_PATH = "manifest.yaml"


def _hash_bytes(data: bytes) -> str:
    """Return a ``sha256:<hex>`` prefixed hash of *data*.

    Args:
        data: Raw bytes to hash.

    Returns:
        ``"sha256:<64-char-hex>"`` string.
    """
    digest = hashlib.sha256(data).hexdigest()
    return f"sha256:{digest}"


class OncpReader:
    """Reads and validates a ``.oncp`` content-addressed zip bundle.

    Usage::

        reader = OncpReader()
        reader.open(Path("/tmp/my_effect.oncp"))

        # Verify all content hashes match the manifest
        assert reader.validate_digests()

        # Inspect the manifest
        manifest = reader.manifest

        # Retrieve individual overlays
        patches = reader.get_overlay_patches()

    The reader is stateful after :meth:`open` — all subsequent calls operate
    on the loaded bundle. Call :meth:`open` again to load a different bundle.

    .. versionadded:: 0.19.0
    """

    def __init__(self) -> None:
        """Initialise the reader in an unopened state."""
        self._manifest: ModelOncpManifest | None = None
        self._zip_bytes: bytes | None = None
        self._source_path: Path | None = None

    # =========================================================================
    # Open
    # =========================================================================

    def open(self, path: Path) -> OncpReader:
        """Load a ``.oncp`` zip bundle from *path*.

        Reads the manifest from ``manifest.yaml`` and validates its schema.
        Content hash verification is deferred to :meth:`validate_digests`.

        Args:
            path: Path to the ``.oncp`` file.

        Returns:
            ``self`` for method chaining.

        Raises:
            ModelOnexError: If *path* does not exist or the zip is invalid.
        """
        if not path.exists():
            raise ModelOnexError(
                f".oncp bundle not found: {path}",
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            )

        raw = path.read_bytes()
        self._zip_bytes = raw
        self._source_path = path
        self._manifest = self._load_manifest(raw)
        return self

    def open_bytes(self, data: bytes) -> OncpReader:
        """Load a ``.oncp`` bundle from in-memory bytes.

        Useful for testing without touching the filesystem.

        Args:
            data: Raw bytes of the ``.oncp`` zip.

        Returns:
            ``self`` for method chaining.

        Raises:
            ModelOnexError: If the zip does not contain a valid ``manifest.yaml``.
        """
        self._zip_bytes = data
        self._source_path = None
        self._manifest = self._load_manifest(data)
        return self

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def manifest(self) -> ModelOncpManifest:
        """Return the loaded manifest.

        Raises:
            ModelOnexError: If :meth:`open` has not been called yet.
        """
        if self._manifest is None:
            raise ModelOnexError(
                "OncpReader.open() must be called before accessing manifest",
                error_code=EnumCoreErrorCode.INVALID_OPERATION,
            )
        return self._manifest

    # =========================================================================
    # Validation
    # =========================================================================

    def validate_digests(self) -> bool:
        """Verify all content hashes recorded in the manifest.

        Checks each overlay, scenario, and invariant entry by reading the
        corresponding zip entry and comparing its SHA-256 digest against the
        hash recorded in the manifest.

        Returns:
            ``True`` if all hashes match.

        Raises:
            ModelOnexError: If :meth:`open` has not been called, or any content hash does not match.
        """
        if self._zip_bytes is None or self._manifest is None:
            raise ModelOnexError(
                "OncpReader.open() must be called before validate_digests()",
                error_code=EnumCoreErrorCode.INVALID_OPERATION,
            )

        mismatches: list[str] = []

        with zipfile.ZipFile(self._zip_bytes_io()) as zf:
            for overlay_entry in self._manifest.overlays:
                actual = _hash_bytes(zf.read(overlay_entry.path))
                if actual != overlay_entry.content_hash:
                    mismatches.append(
                        f"overlay '{overlay_entry.overlay_id}': "
                        f"expected {overlay_entry.content_hash}, got {actual}"
                    )

            for scenario_entry in self._manifest.scenarios:
                actual = _hash_bytes(zf.read(scenario_entry.path))
                if actual != scenario_entry.content_hash:
                    mismatches.append(
                        f"scenario '{scenario_entry.id}': "
                        f"expected {scenario_entry.content_hash}, got {actual}"
                    )

            for invariant_entry in self._manifest.invariants:
                actual = _hash_bytes(zf.read(invariant_entry.path))
                if actual != invariant_entry.content_hash:
                    mismatches.append(
                        f"invariant '{invariant_entry.id}': "
                        f"expected {invariant_entry.content_hash}, got {actual}"
                    )

        if mismatches:
            raise ModelOnexError(
                "Content hash mismatch(es) in .oncp bundle:\n"
                + "\n".join(f"  - {m}" for m in mismatches),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        return True

    # =========================================================================
    # Data accessors
    # =========================================================================

    def get_overlay_patches(self) -> list[ModelContractPatch]:
        """Return all overlay patches in application order.

        Parses each overlay YAML entry back into a :class:`ModelContractPatch`.

        Returns:
            List of patches in ascending ``order_index`` order.

        Raises:
            ModelOnexError: If :meth:`open` has not been called.
        """
        if self._zip_bytes is None or self._manifest is None:
            raise ModelOnexError(
                "OncpReader.open() must be called before get_overlay_patches()",
                error_code=EnumCoreErrorCode.INVALID_OPERATION,
            )

        sorted_overlays = sorted(self._manifest.overlays, key=lambda e: e.order_index)

        patches: list[ModelContractPatch] = []
        with zipfile.ZipFile(self._zip_bytes_io()) as zf:
            for entry in sorted_overlays:
                raw = zf.read(entry.path)
                data = yaml.safe_load(raw.decode("utf-8"))
                patches.append(ModelContractPatch.model_validate(data))

        return patches

    def list_scenarios(self) -> list[ModelOncpScenarioEntry]:
        """Return the scenario entries recorded in the manifest.

        Returns:
            List of :class:`ModelOncpScenarioEntry` as declared in the manifest.

        Raises:
            RuntimeError: If :meth:`open` has not been called.
        """
        return list(self.manifest.scenarios)

    def get_scenario_content(self, scenario_id: str) -> bytes:
        """Return the raw bytes of a named scenario entry.

        Args:
            scenario_id: The ``id`` of the scenario to retrieve.

        Returns:
            Raw bytes of the scenario YAML.

        Raises:
            ModelOnexError: If :meth:`open` has not been called, or no scenario with the given id exists.
        """
        if self._zip_bytes is None or self._manifest is None:
            raise ModelOnexError(
                "OncpReader.open() must be called before get_scenario_content()",
                error_code=EnumCoreErrorCode.INVALID_OPERATION,
            )

        for entry in self._manifest.scenarios:
            if entry.id == scenario_id:
                with zipfile.ZipFile(self._zip_bytes_io()) as zf:
                    return zf.read(entry.path)

        raise ModelOnexError(
            f"No scenario with id '{scenario_id}' in bundle",
            error_code=EnumCoreErrorCode.INVALID_INPUT,
        )

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _zip_bytes_io(self) -> io.BytesIO:
        """Return the buffered zip bytes as a seekable BytesIO.

        Returns:
            ``io.BytesIO`` wrapping the zip data.

        Raises:
            ModelOnexError: If not opened yet.
        """
        if self._zip_bytes is None:
            raise ModelOnexError(
                "OncpReader.open() must be called first",
                error_code=EnumCoreErrorCode.INVALID_OPERATION,
            )
        return io.BytesIO(self._zip_bytes)

    @staticmethod
    def _load_manifest(zip_data: bytes) -> ModelOncpManifest:
        """Parse and validate ``manifest.yaml`` from raw zip bytes.

        Args:
            zip_data: Raw bytes of the ``.oncp`` zip.

        Returns:
            Validated :class:`ModelOncpManifest`.

        Raises:
            ModelOnexError: If ``manifest.yaml`` is absent or the zip is invalid.
        """
        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                if _MANIFEST_PATH not in zf.namelist():
                    raise ModelOnexError(
                        f".oncp bundle is missing '{_MANIFEST_PATH}'",
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    )
                raw = zf.read(_MANIFEST_PATH)
        except zipfile.BadZipFile as exc:
            raise ModelOnexError(
                f"Not a valid zip/oncp file: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc

        data = yaml.safe_load(raw.decode("utf-8"))
        return ModelOncpManifest.model_validate(data)
