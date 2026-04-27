# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Legacy DoD receipt migration utility (OMN-9790).

The OMN-9786 PR added four required fields to ``ModelDodReceipt``:
``verifier``, ``probe_command``, ``probe_stdout``, and ``schema_version``.
Receipts on disk that pre-date that change cannot validate against the new
schema and would silently degrade the receipt-gate to FAIL.

This module rewrites legacy receipts in-place so they validate as ADVISORY
(per the Centralized Transition Policy in :mod:`omnibase_core.models.contracts.ticket.model_dod_receipt`).

The receipt itself is rewritten to satisfy the post-OMN-9786 schema. Audit
metadata about the migration (the prior ``status`` value and the migration
timestamp) is written to a sidecar file alongside the receipt — never into
the receipt body, because ``ModelDodReceipt`` is configured with
``extra="forbid"`` and would reject unknown top-level keys. The sidecar is
named ``<receipt_stem>.migration.<format>`` (yaml or json, matching the
receipt's own format).

Two entry points are exposed:

* :func:`migrate_receipt_file` — migrate a single receipt path
* :func:`migrate_receipts_in_root` — walk ``drift/dod_receipts/`` and
  ``.evidence/`` under a repo root and migrate every legacy receipt found

Both functions are idempotent: a receipt that already carries a ``verifier``
field is treated as already-migrated and left byte-identical.

The CLI entry point lives in ``scripts/migrate_dod_receipts.py`` (at repo
root) so this module can be imported without side effects.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Sentinel values backfilled into legacy receipts. ``verifier`` is the
# only one with semantic weight — it triggers the ``verifier == runner``
# check elsewhere in the gate, but legacy receipts use the dedicated
# ``legacy-self-attested`` literal so audits can distinguish "self-attested
# pre-policy" from "self-attested post-policy".
LEGACY_VERIFIER_SENTINEL = "legacy-self-attested"
SENTINEL_PROBE_COMMAND = ""
SENTINEL_PROBE_STDOUT = ""
SENTINEL_SCHEMA_VERSION = "0.0.0"

# Status assigned to migrated receipts. ADVISORY is non-blocking but
# visible — exactly the right signal for "this came from before the
# adversarial-invariants policy and cannot be retroactively trusted".
_MIGRATED_STATUS = "ADVISORY"

# Subdirectories under a repo root that hold receipts. Order matters only
# for the deterministic walk in :func:`migrate_receipts_in_root`.
_RECEIPT_LOCATIONS: tuple[tuple[str, ...], ...] = (
    ("drift", "dod_receipts"),
    (".evidence",),
)

# File suffixes recognized as receipts. Anything else is a no-op so the
# walker can be pointed at directories that contain other artifacts.
_YAML_SUFFIXES = frozenset({".yaml", ".yml"})
_JSON_SUFFIXES = frozenset({".json"})


@allow_dict_any(reason="Receipt YAML/JSON payloads are heterogeneous by design")
def _parse(path: Path) -> tuple[dict[str, Any], str]:
    """Parse ``path`` and return (data, format_tag).

    ``format_tag`` is ``"yaml"`` or ``"json"``. Raises ``ModelOnexError`` for
    missing files, unparseable contents, or non-mapping top-level structures.
    """
    if not path.exists():
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"receipt path does not exist: {path}",
            context={"path": str(path)},
        )

    text = path.read_text()
    suffix = path.suffix.lower()
    if suffix in _YAML_SUFFIXES:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"failed to parse YAML receipt {path}: {exc}",
                context={"path": str(path)},
            ) from exc
        format_tag = "yaml"
    elif suffix in _JSON_SUFFIXES:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"failed to parse JSON receipt {path}: {exc}",
                context={"path": str(path)},
            ) from exc
        format_tag = "json"
    else:  # pragma: no cover — guarded by caller
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"unsupported receipt suffix: {path.suffix}",
            context={"path": str(path)},
        )

    if not isinstance(data, dict):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"receipt {path} must be a mapping at the top level, got {type(data).__name__}",
            context={"path": str(path), "actual_type": type(data).__name__},
        )
    return data, format_tag


@allow_dict_any(reason="Receipt YAML/JSON payloads are heterogeneous by design")
def _serialize(data: dict[str, Any], format_tag: str) -> str:
    """Re-serialize ``data`` in its original format.

    YAML uses ``sort_keys=False`` so the diff matches the human-edited
    field order; JSON uses ``indent=2`` to match the existing receipts in
    ``.evidence/`` (verified by spot check 2026-04-26).
    """
    if format_tag == "yaml":
        return yaml.safe_dump(data, sort_keys=False)
    if format_tag == "json":
        return json.dumps(data, indent=2) + "\n"
    raise ModelOnexError(  # pragma: no cover
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        message=f"unsupported format tag: {format_tag}",
        context={"format_tag": format_tag},
    )


def _sidecar_path(receipt_path: Path, format_tag: str) -> Path:
    """Return the path for the migration audit sidecar next to ``receipt_path``.

    The sidecar uses the same format as the receipt so a human inspecting
    the directory sees a single consistent file format.
    """
    suffix = ".yaml" if format_tag == "yaml" else ".json"
    return receipt_path.with_name(f"{receipt_path.stem}.migration{suffix}")


@allow_dict_any(reason="Migrating heterogeneous receipt YAML/JSON payloads in place")
def migrate_receipt_file(path: Path) -> bool:
    """Migrate a single receipt file in place.

    The receipt body is rewritten to satisfy ``ModelDodReceipt`` (status
    downgraded to ADVISORY plus the four OMN-9786 sentinel fields). Audit
    metadata (``original_status``, ``migrated_at``) is written to a sidecar
    file next to the receipt — ``ModelDodReceipt`` is configured with
    ``extra="forbid"`` and would reject those keys on the receipt itself.

    Returns ``True`` if the file was rewritten, ``False`` if it was left
    untouched (already migrated or unsupported suffix).

    Raises:
        ModelOnexError: if the file does not exist, fails to parse, or
            contains a non-mapping top-level structure. Callers that need
            to keep walking on bad input should catch this.
    """
    suffix = path.suffix.lower()
    if suffix not in _YAML_SUFFIXES and suffix not in _JSON_SUFFIXES:
        return False

    data, format_tag = _parse(path)

    # Idempotency: presence of ``verifier`` is the migration tombstone.
    if "verifier" in data:
        return False

    original_status = data.get("status", "UNKNOWN")
    # Backfill happens in a fresh dict so insertion order is deterministic
    # and predictable across re-runs (important for byte-identical
    # idempotency on the second pass — see test_running_migration_twice).
    migrated: dict[str, Any] = dict(data)
    migrated["status"] = _MIGRATED_STATUS
    migrated["verifier"] = LEGACY_VERIFIER_SENTINEL
    migrated["probe_command"] = SENTINEL_PROBE_COMMAND
    migrated["probe_stdout"] = SENTINEL_PROBE_STDOUT
    migrated["schema_version"] = SENTINEL_SCHEMA_VERSION

    audit: dict[str, Any] = {
        "original_status": original_status,
        "migrated_at": datetime.now(tz=UTC).isoformat(),
        "receipt_file": path.name,
    }

    path.write_text(_serialize(migrated, format_tag))
    _sidecar_path(path, format_tag).write_text(_serialize(audit, format_tag))
    return True


def migrate_receipts_in_root(root: Path, *, dry_run: bool = False) -> tuple[int, int]:
    """Walk receipt locations under ``root`` and migrate every legacy receipt.

    The walker visits ``drift/dod_receipts/`` and ``.evidence/`` recursively,
    inspecting both ``*.yaml``/``*.yml`` and ``*.json`` files. Files that
    raise ``ModelOnexError`` during migration are surfaced — callers that want
    "skip and continue" semantics should catch the exception themselves.

    Args:
        root: repo root containing receipt directories.
        dry_run: if True, count what *would* be migrated but do not write.
            A dry-run still counts a legacy receipt as "would be modified",
            i.e. the first element of the return tuple.

    Returns:
        ``(modified, skipped)`` — counts of files that were rewritten (or
        would be, in dry-run mode) versus those left unchanged.
    """
    modified = 0
    skipped = 0
    for parts in _RECEIPT_LOCATIONS:
        loc = root.joinpath(*parts)
        if not loc.exists():
            continue
        for path in sorted(loc.rglob("*")):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix not in _YAML_SUFFIXES and suffix not in _JSON_SUFFIXES:
                continue
            # Skip sidecar audit files written by previous migration runs;
            # they are not receipts and would otherwise be misclassified.
            if path.name.endswith(
                (".migration.yaml", ".migration.yml", ".migration.json")
            ):
                continue
            if dry_run:
                # Re-parse to decide modified-vs-skipped without writing.
                data, _ = _parse(path)
                if "verifier" in data:
                    skipped += 1
                else:
                    modified += 1
                continue
            if migrate_receipt_file(path):
                modified += 1
            else:
                skipped += 1
    return modified, skipped


__all__ = [
    "LEGACY_VERIFIER_SENTINEL",
    "SENTINEL_PROBE_COMMAND",
    "SENTINEL_PROBE_STDOUT",
    "SENTINEL_SCHEMA_VERSION",
    "migrate_receipt_file",
    "migrate_receipts_in_root",
]
