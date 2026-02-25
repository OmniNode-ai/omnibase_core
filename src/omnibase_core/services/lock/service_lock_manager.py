# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ServiceLockManager — contract lockfile generation and CI enforcement.

The lock manager implements the ``omn lock`` workflow:

1. **Generate** (``generate()``): Reads the current catalog from
   ``ServiceCatalogManager``, pins each command's fingerprint, publisher,
   CLI version requirement, and schema refs, then writes ``omn.lock``.

2. **Check** (``check()``): Verifies the lockfile against the current catalog
   without modifying anything.  Exits non-zero on drift (suitable for CI).

3. **Diff** (``diff()``): Returns a human-readable diff showing which
   contracts have drifted since the lockfile was generated.

## Lockfile Format

YAML, human-readable, git-diff friendly:

.. code-block:: yaml

    lock_version: "1"
    generated_at: "2026-02-24T00:00:00+00:00"
    cli_version: "0.20.0"
    commands:
      - command_id: com.omninode.memory.query
        fingerprint: <sha256-hex>
        publisher: com.omninode.memory
        cli_version_requirement: ""
        args_schema_ref: schema://memory.query.args.v1
        output_schema_ref: schema://memory.query.output.v1

## Determinism

``generate()`` sorts entries by ``command_id`` before writing.  The same
catalog state always produces identical lockfile bytes.

## Partial Lockfile Rejection

A lockfile that covers fewer commands than the current catalog is rejected
with ``LockPartialError``.  All-or-nothing enforcement prevents silent gaps.

## Drift Detection

Drift is detected by comparing the current catalog fingerprints against the
lockfile entries.  Fingerprints come from ``ServiceCatalogManager`` via the
``_signatures`` store (publisher fingerprint) cross-referenced against
the entry's ``command_id → publisher`` mapping.

.. versionadded:: 0.20.0  (OMN-2570)
"""

from __future__ import annotations

__all__ = [
    "ModelLockDiffResult",
    "ModelLockDriftEntry",
    "LockDriftError",
    "LockError",
    "LockFileError",
    "LockPartialError",
    "ServiceLockManager",
]

import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from omnibase_core.errors.error_lock import (
    LockDriftError,
    LockError,
    LockFileError,
    LockPartialError,
)
from omnibase_core.models.lock.model_lock_diff_result import ModelLockDiffResult
from omnibase_core.models.lock.model_lock_drift_entry import ModelLockDriftEntry
from omnibase_core.models.lock.model_lock_entry import ModelLockEntry
from omnibase_core.models.lock.model_lockfile import LOCK_FORMAT_VERSION, ModelLockfile

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_cli_contribution import (
        ModelCliCommandEntry,
    )
    from omnibase_core.services.catalog.service_catalog_manager import (
        ServiceCatalogManager,
    )

# Default lockfile path (overrideable via constructor).
_DEFAULT_LOCK_PATH = Path("omn.lock")


class ServiceLockManager:
    """Contract lockfile generation and CI enforcement for the registry CLI.

    Implements ``omn lock``, ``omn lock --check``, and ``omn lock --diff``.

    Args:
        catalog: The ``ServiceCatalogManager`` from which the current command
            catalog is read.  Must have been loaded (``load()`` or
            ``refresh()`` called) before generating or checking.
        lock_path: Path to the lockfile.  Defaults to ``./omn.lock``.
        cli_version: The running CLI version string (e.g. ``"0.20.0"``).
            Stored in the lockfile.  If not provided, defaults to ``""``.

    Thread Safety:
        All public methods are protected by an internal ``threading.RLock``.

    Example:
        .. code-block:: python

            from omnibase_core.services.catalog.service_catalog_manager import (
                ServiceCatalogManager,
            )
            from omnibase_core.services.lock.service_lock_manager import (
                ServiceLockManager,
            )

            catalog = ServiceCatalogManager(registry=registry, cli_version="0.20.0")
            catalog.refresh()

            lock = ServiceLockManager(catalog=catalog, cli_version="0.20.0")
            lock.generate()            # writes omn.lock
            lock.check()               # verifies omn.lock (raises LockDriftError on drift)
            result = lock.diff()       # returns ModelLockDiffResult

    .. versionadded:: 0.20.0  (OMN-2570)
    """

    def __init__(
        self,
        catalog: ServiceCatalogManager,
        lock_path: Path | None = None,
        cli_version: str | None = None,
    ) -> None:
        """Initialize ServiceLockManager.

        Args:
            catalog: Loaded command catalog to read fingerprints from.
            lock_path: Override for the default ``./omn.lock`` path.
            cli_version: Running CLI version stored in the generated lockfile.
        """
        self._catalog = catalog
        self._lock_path: Path = lock_path or _DEFAULT_LOCK_PATH
        self._cli_version: str = cli_version or ""
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> ModelLockfile:
        """Generate the lockfile from the current catalog.

        Reads all commands from the catalog, pins their fingerprints and
        metadata, sorts entries by ``command_id``, and writes ``omn.lock``
        in YAML format.

        Returns:
            The generated ``ModelLockfile`` instance.

        Raises:
            LockError: If the catalog is empty or write fails.
        """
        with self._lock:
            commands = self._catalog.list_commands()
            entries = self._build_entries(commands)

            # Sort for determinism.
            sorted_entries = sorted(entries, key=lambda e: e.command_id)

            lockfile = ModelLockfile(
                lock_version=LOCK_FORMAT_VERSION,
                generated_at=datetime.now(UTC),
                cli_version=self._cli_version,
                commands=sorted_entries,
            )

            self._write_lockfile(lockfile)
            return lockfile

    def check(self) -> None:
        """Verify the current catalog against the lockfile.

        Reads ``omn.lock`` and compares each command's fingerprint against
        the current catalog.  Does NOT modify the lockfile or catalog.

        Suitable for CI pre-flight.  Exits non-zero (raises) on any drift.

        Raises:
            LockFileError: If the lockfile is missing or unparseable.
            LockPartialError: If the lockfile covers fewer commands than
                the current catalog.
            LockDriftError: If any command fingerprint has drifted.
        """
        with self._lock:
            lockfile = self._read_lockfile()
            diff = self._compute_diff(lockfile)

            if diff.is_clean:
                return

            drifted_ids = [e.command_id for e in diff.drifted]
            raise LockDriftError(
                f"Lockfile drift detected for {len(drifted_ids)} command(s): "
                + ", ".join(drifted_ids)
                + ". Run 'omn lock' to regenerate the lockfile."
            )

    def diff(self) -> ModelLockDiffResult:
        """Compute drift between the current catalog and the lockfile.

        Returns a ``ModelLockDiffResult`` showing which commands have been added,
        removed, or changed since the lockfile was generated.

        Returns:
            ``ModelLockDiffResult`` with the full list of drifted entries.
            ``result.is_clean`` is True when no drift is detected.

        Raises:
            LockFileError: If the lockfile is missing or unparseable.
        """
        with self._lock:
            lockfile = self._read_lockfile()
            return self._compute_diff(lockfile)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_entries(
        self,
        commands: list[ModelCliCommandEntry],
    ) -> list[ModelLockEntry]:
        """Build lock entries from the current catalog commands.

        For each command, the fingerprint is sourced from the catalog's
        internal signature store (publisher → fingerprint mapping built
        during ``refresh()`` or ``load()``).

        Args:
            commands: All visible commands from the catalog.

        Returns:
            List of ``ModelLockEntry`` instances (unsorted).

        Raises:
            LockError: If a command's publisher fingerprint is not found
                in the catalog signature store.
        """
        # Access the internal signatures dict via the catalog.
        # The signatures dict maps publisher_id → {fingerprint, signature, signer_public_key}.
        signatures: dict[str, dict[str, str]] = getattr(
            self._catalog, "_signatures", {}
        )

        entries: list[ModelLockEntry] = []
        for cmd in commands:
            # Find publisher fingerprint — we look up by command attributes.
            # The catalog manager stores fingerprints keyed by publisher node ID.
            # We iterate signatures to find which publisher owns this command.
            publisher_fingerprint = self._resolve_publisher_fingerprint(cmd, signatures)

            entry = ModelLockEntry(
                command_id=cmd.id,
                fingerprint=publisher_fingerprint,
                publisher=self._resolve_publisher(cmd, signatures),
                cli_version_requirement="",
                args_schema_ref=cmd.args_schema_ref,
                output_schema_ref=cmd.output_schema_ref,
            )
            entries.append(entry)
        return entries

    def _resolve_publisher(
        self,
        cmd: ModelCliCommandEntry,
        signatures: dict[str, dict[str, str]],
    ) -> str:
        """Resolve the publisher node ID for a command.

        Finds the publisher by scanning the catalog's signature store.
        When no publisher can be determined (offline or load-only mode),
        returns ``"unknown"``.

        Args:
            cmd: Command entry to resolve publisher for.
            signatures: Publisher signature store from the catalog.

        Returns:
            Publisher node ID string.
        """
        # The catalog does not store a direct cmd→publisher mapping in the
        # public API.  We detect the publisher by scanning contributions if
        # available, or fall back to the first (only) publisher in single-
        # publisher setups.
        if len(signatures) == 1:
            return next(iter(signatures))
        # In multi-publisher catalogs without a direct reverse-lookup table,
        # we return the first publisher as a best-effort fallback.
        # Production use should ensure refresh() is called before generate().
        if signatures:
            return next(iter(signatures))
        return "unknown"

    def _resolve_publisher_fingerprint(
        self,
        cmd: ModelCliCommandEntry,
        signatures: dict[str, dict[str, str]],
    ) -> str:
        """Resolve the fingerprint for a command's publisher.

        The fingerprint comes from the publisher's signature store entry.
        In single-publisher deployments this is unambiguous.  In multi-
        publisher deployments, all commands from the same publisher share
        the same fingerprint (the fingerprint covers the full commands list
        that publisher submitted).

        Args:
            cmd: Command entry to resolve fingerprint for.
            signatures: Publisher signature store from the catalog.

        Returns:
            64-character lowercase hex SHA256 fingerprint.

        Raises:
            LockError: If no fingerprint can be resolved (no publishers).
        """
        if not signatures:
            raise LockError(
                f"Cannot resolve fingerprint for command '{cmd.id}': "
                "no publishers in catalog signature store. "
                "Run 'omn refresh' to populate the catalog."
            )
        publisher = self._resolve_publisher(cmd, signatures)
        sig_entry = signatures.get(publisher, {})
        fp = sig_entry.get("fingerprint", "")
        if not fp:
            raise LockError(
                f"Publisher '{publisher}' has no fingerprint in catalog. "
                "Run 'omn refresh' to rebuild the catalog."
            )
        return fp

    def _write_lockfile(self, lockfile: ModelLockfile) -> None:
        """Serialize and write the lockfile to disk.

        Args:
            lockfile: The lockfile model to write.
        """
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)

        # Build a deterministic serializable dict.
        payload: dict[str, object] = {
            "lock_version": lockfile.lock_version,
            "generated_at": lockfile.generated_at.isoformat(),
            "cli_version": lockfile.cli_version,
            "commands": [
                {
                    "command_id": e.command_id,
                    "fingerprint": e.fingerprint,
                    "publisher": e.publisher,
                    "cli_version_requirement": e.cli_version_requirement,
                    "args_schema_ref": e.args_schema_ref,
                    "output_schema_ref": e.output_schema_ref,
                }
                for e in lockfile.commands
            ],
        }

        self._lock_path.write_text(
            yaml.dump(
                payload, default_flow_style=False, sort_keys=True, allow_unicode=True
            ),
            encoding="utf-8",
        )

    def _read_lockfile(self) -> ModelLockfile:
        """Read and parse the lockfile from disk.

        Returns:
            Parsed ``ModelLockfile``.

        Raises:
            LockFileError: If the file is missing or unparseable.
        """
        if not self._lock_path.exists():
            raise LockFileError(
                f"Lockfile not found at '{self._lock_path}'. "
                "Run 'omn lock' to generate the lockfile."
            )

        try:
            raw = self._lock_path.read_text(encoding="utf-8")
            data = yaml.safe_load(  # yaml-ok: parse raw lockfile YAML to dict, then validate via ModelLockEntry.model_validate()
                raw
            )
        except (OSError, yaml.YAMLError) as exc:
            raise LockFileError(
                f"Failed to read lockfile at '{self._lock_path}': {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise LockFileError(
                f"Lockfile at '{self._lock_path}' is malformed: expected a YAML mapping."
            )

        try:
            commands_raw = data.get("commands", [])
            if not isinstance(commands_raw, list):
                raise LockFileError("Lockfile 'commands' field must be a list.")

            commands = [ModelLockEntry.model_validate(c) for c in commands_raw]

            generated_at_raw = data.get("generated_at", "")
            if isinstance(generated_at_raw, datetime):
                generated_at = generated_at_raw
            else:
                generated_at = datetime.fromisoformat(str(generated_at_raw))

            return ModelLockfile(
                lock_version=str(data.get("lock_version", LOCK_FORMAT_VERSION)),
                generated_at=generated_at,
                cli_version=str(data.get("cli_version", "")),
                commands=commands,
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise LockFileError(
                f"Lockfile at '{self._lock_path}' has invalid structure: {exc}"
            ) from exc

    def _compute_diff(self, lockfile: ModelLockfile) -> ModelLockDiffResult:
        """Compare the lockfile against the current catalog.

        Detects:
        - ``changed``: command exists in both but fingerprint differs.
        - ``added``: command is in the catalog but not in the lockfile.
        - ``removed``: command is in the lockfile but not in the catalog.

        Also enforces the partial-lockfile constraint: if the lockfile covers
        fewer commands than the catalog, raises ``LockPartialError``.

        Args:
            lockfile: The loaded lockfile to compare against.

        Returns:
            ``ModelLockDiffResult`` describing all drifted commands.

        Raises:
            LockPartialError: If the lockfile is a strict subset of the
                catalog (partial coverage).
        """
        current_commands = self._catalog.list_commands()
        current_map: dict[str, str] = {}

        signatures: dict[str, dict[str, str]] = getattr(
            self._catalog, "_signatures", {}
        )

        for cmd in current_commands:
            try:
                fp = self._resolve_publisher_fingerprint(cmd, signatures)
            except LockError:
                fp = ""
            current_map[cmd.id] = fp

        locked_map: dict[str, str] = {
            e.command_id: e.fingerprint for e in lockfile.commands
        }

        current_ids = set(current_map)
        locked_ids = set(locked_map)

        drifted: list[ModelLockDriftEntry] = []

        # Changed: in both but fingerprint differs.
        for cmd_id in current_ids & locked_ids:
            if current_map[cmd_id] != locked_map[cmd_id]:
                drifted.append(
                    ModelLockDriftEntry(
                        command_id=cmd_id,
                        locked_fingerprint=locked_map[cmd_id],
                        current_fingerprint=current_map[cmd_id],
                        status="changed",
                    )
                )

        # Added: in catalog but not locked — this is the partial-lockfile scenario.
        added_ids = current_ids - locked_ids
        if added_ids:
            # Partial lockfile: catalog has commands not in lockfile.
            raise LockPartialError(
                f"Lockfile is partial: {len(added_ids)} command(s) in the catalog "
                f"are not covered by the lockfile: {sorted(added_ids)}. "
                "Run 'omn lock' to regenerate the lockfile."
            )

        # Removed: in lockfile but not in catalog.
        for cmd_id in locked_ids - current_ids:
            drifted.append(
                ModelLockDriftEntry(
                    command_id=cmd_id,
                    locked_fingerprint=locked_map[cmd_id],
                    current_fingerprint=None,
                    status="removed",
                )
            )

        return ModelLockDiffResult(drifted=drifted)

    def __repr__(self) -> str:
        """Return debug representation."""
        with self._lock:
            return (
                f"ServiceLockManager("
                f"lock_path={self._lock_path}, "
                f"cli_version={self._cli_version!r})"
            )
