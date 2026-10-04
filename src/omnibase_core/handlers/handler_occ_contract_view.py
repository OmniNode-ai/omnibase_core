# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One ticket's OCC contract read across both layouts (OMN-20068).

A ticket's ``dod_evidence`` used to live in exactly one file::

    contracts/<TICKET>.yaml                      # legacy, shared by every companion

Every change-control companion for a ticket appended to that one file, so each
companion that merged put every other open companion for the ticket back into a
git conflict. A companion now writes its own file instead::

    contracts/<TICKET>/<REPO>-<PR>.yaml           # per-PR, one per companion

Readers take the union of both. Nothing is migrated: a ticket whose evidence is
only in the legacy file reads exactly as before, the per-PR directory adds to it,
and no merged record is rewritten.

Validation is no looser than the single-file read:

* the legacy file must parse, as before;
* every file in the per-PR directory must be named ``<repo>-<pr>.yaml``, parse
  to a mapping, declare ``ticket_id`` equal to the directory's ticket and carry
  a non-empty ``dod_evidence`` list of mappings, each with a string ``id``;
* a ``dod_evidence`` id may appear in only one file across both layouts.

Any violation raises :class:`ModelOnexError` with ``CONTRACT_VALIDATION_ERROR``;
callers fail closed on it the same way they fail on an unreadable legacy file.

Hash binding stays per file. A receipt's whole-file ``contract_sha256`` is
compared with the sha256 of the file that holds its entry (see
:meth:`ModelOccContractView.source_for`), and the per-entry
``contract_entry_sha256`` is computed over that same file's parsed mapping, so
the header fields it folds in (``ticket_id``, ``schema_version``) are the ones
the companion wrote. Adding a new per-PR file therefore never changes the hash
of any existing entry, in either layout.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_occ_contract_source import (
    ModelOccContractSource,
)
from omnibase_core.models.validation.model_occ_contract_view import (
    ModelOccContractView,
)

__all__ = [
    "PER_PR_CONTRACT_FILENAME_PATTERN",
    "legacy_contract_path",
    "load_occ_contract_view",
    "occ_contract_present",
    "per_pr_contract_dir",
    "per_pr_contract_path",
]

# ``<repo>-<pr>.yaml``: the repo is the short repository name (as in
# ``omnibase_core``), the PR its number. The repo may itself contain hyphens; the
# last ``-<digits>`` is the PR number.
PER_PR_CONTRACT_FILENAME_PATTERN = re.compile(
    r"^(?P<repo>[A-Za-z0-9_.][A-Za-z0-9_.-]*)-(?P<pr>[1-9][0-9]*)\.yaml$"
)


def _view_error(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
    )


def legacy_contract_path(contracts_dir: Path, ticket_id: str) -> Path:
    """``contracts/<TICKET>.yaml``."""
    return contracts_dir / f"{ticket_id}.yaml"


def per_pr_contract_dir(contracts_dir: Path, ticket_id: str) -> Path:
    """``contracts/<TICKET>/``."""
    return contracts_dir / ticket_id


def per_pr_contract_path(
    contracts_dir: Path, ticket_id: str, repo: str, pr_number: int
) -> Path:
    """``contracts/<TICKET>/<REPO>-<PR>.yaml``: the one file a companion writes.

    ``repo`` may be ``owner/name``; only the name is used.
    """
    short_repo = repo.rsplit("/", 1)[-1]
    name = f"{short_repo}-{pr_number}.yaml"
    if PER_PR_CONTRACT_FILENAME_PATTERN.fullmatch(name) is None:
        raise _view_error(
            f"cannot build a per-PR contract name from repo={repo!r} pr={pr_number!r}"
        )
    return per_pr_contract_dir(contracts_dir, ticket_id) / name


def occ_contract_present(contracts_dir: Path, ticket_id: str) -> bool:
    """True when either layout has a file for ``ticket_id``."""
    if legacy_contract_path(contracts_dir, ticket_id).is_file():
        return True
    per_pr_dir = per_pr_contract_dir(contracts_dir, ticket_id)
    return per_pr_dir.is_dir() and any(per_pr_dir.iterdir())


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _load_yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as fh:
        return yaml.load(fh, Loader=yaml.SafeLoader)


def _evidence_ids(data: object) -> list[str]:
    if not isinstance(data, dict):
        return []
    items = data.get("dod_evidence", [])
    if not isinstance(items, list):
        return []
    return [
        item["id"]
        for item in items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]


def _load_per_pr_source(path: Path, ticket_id: str) -> ModelOccContractSource:
    if PER_PR_CONTRACT_FILENAME_PATTERN.fullmatch(path.name) is None:
        raise _view_error(f"per-PR contract {path} is not named <repo>-<pr>.yaml")
    if not path.is_file():
        raise _view_error(f"per-PR contract {path} is not a file")
    try:
        data = _load_yaml(path)
        digest = _sha256_file(path)
    except (OSError, yaml.YAMLError) as exc:
        raise _view_error(f"per-PR contract {path} is unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise _view_error(f"per-PR contract {path} is not a mapping")
    declared = data.get("ticket_id")
    if not isinstance(declared, str) or declared.strip().upper() != ticket_id.upper():
        raise _view_error(
            f"per-PR contract {path} declares ticket_id={declared!r}, "
            f"expected {ticket_id!r}"
        )
    items = data.get("dod_evidence")
    if not isinstance(items, list) or not items:
        raise _view_error(f"per-PR contract {path} has no dod_evidence items")
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise _view_error(
                f"per-PR contract {path} has a dod_evidence item without a string id"
            )
    return ModelOccContractSource(path=path, sha256=digest, data=data, is_legacy=False)


def load_occ_contract_view(
    contracts_dir: Path, ticket_id: str
) -> ModelOccContractView | None:
    """Read ``ticket_id``'s contract from both layouts.

    Returns ``None`` when neither ``contracts/<TICKET>.yaml`` nor any file under
    ``contracts/<TICKET>/`` exists. Raises :class:`ModelOnexError` with
    ``CONTRACT_VALIDATION_ERROR`` when a file exists but the union is not a
    valid contract (see module docstring).

    With only the legacy file, :attr:`ModelOccContractView.data` is that file's
    parsed content, unchanged. With per-PR files it is the legacy mapping (or
    ``{"ticket_id": ticket_id}`` when there is none) with ``dod_evidence``
    replaced by the legacy items followed by each per-PR file's items in
    file-name order.
    """
    sources: list[ModelOccContractSource] = []

    legacy_path = legacy_contract_path(contracts_dir, ticket_id)
    if legacy_path.is_file():
        try:
            legacy_data = _load_yaml(legacy_path)
            legacy_hash = _sha256_file(legacy_path)
        except (OSError, yaml.YAMLError) as exc:
            raise _view_error(f"contract {legacy_path} is unreadable: {exc}") from exc
        sources.append(
            ModelOccContractSource(
                path=legacy_path, sha256=legacy_hash, data=legacy_data, is_legacy=True
            )
        )

    per_pr_dir = per_pr_contract_dir(contracts_dir, ticket_id)
    if per_pr_dir.is_dir():
        sources.extend(
            _load_per_pr_source(path, ticket_id)
            for path in sorted(per_pr_dir.iterdir(), key=lambda p: p.name)
        )

    if not sources:
        return None

    entry_sources: dict[str, ModelOccContractSource] = {}
    merged_items: list[object] = []
    for source in sources:
        seen_here: set[str] = set()
        for evidence_id in _evidence_ids(source.data):
            owner = entry_sources.get(evidence_id)
            if owner is not None and owner is not source:
                raise _view_error(
                    f"dod_evidence id {evidence_id!r} is declared in both "
                    f"{owner.path} and {source.path}"
                )
            if evidence_id in seen_here and not source.is_legacy:
                raise _view_error(
                    f"dod_evidence id {evidence_id!r} is declared twice in "
                    f"{source.path}"
                )
            seen_here.add(evidence_id)
            entry_sources.setdefault(evidence_id, source)
        if isinstance(source.data, dict):
            items = source.data.get("dod_evidence", [])
            if isinstance(items, list):
                merged_items.extend(items)

    legacy = next((s for s in sources if s.is_legacy), None)
    data: object
    if legacy is not None and len(sources) == 1:
        # Legacy-only: exactly what the single-file read returned.
        data = legacy.data
    elif legacy is not None and not isinstance(legacy.data, dict):
        raise _view_error(
            f"contract {legacy.path} is not a mapping, so the per-PR files under "
            f"{per_pr_dir} cannot be added to it"
        )
    else:
        base: dict[str, object] = {"ticket_id": ticket_id}
        if legacy is not None and isinstance(legacy.data, dict):
            base = dict(legacy.data)
        base["dod_evidence"] = merged_items
        data = base

    return ModelOccContractView(
        ticket_id=ticket_id,
        sources=tuple(sources),
        data=data,
        entry_sources=entry_sources,
    )
