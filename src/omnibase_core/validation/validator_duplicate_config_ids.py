# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ValidatorDuplicateConfigIds — reject config/registry YAML files that declare
duplicate ids over a key that is not guaranteed unique.

Background (OMN-14401):
    Two independent production bugs shared the same shape: a lookup key that
    was assumed unique (grant ``(runtime_lane, image_digest)``, model routing
    ``id``) stopped being unique, and the consuming resolver's first-match-wins
    logic silently picked the wrong record (OMN-14395, OMN-14396). Neither had
    a test or a gate pinning the uniqueness/disambiguation rule — both were
    found only by adversarial verification, after the fact.

    yamllint's ``key-duplicates`` rule (where configured) does NOT catch this
    class: it only flags duplicate *mapping* keys, never duplicate `id:` (or
    similar) *field values* across sibling *list items* — which is exactly the
    shape both real bugs took. This validator closes that specific gap.

Design (config-as-data):
    The set of checked registries is declared in a manifest YAML file (default
    ``.duplicate-id-registries.yaml`` at the repo root, see
    ``ModelDuplicateIdManifest``), not in code. Adding a new registry to the
    checked set is a config change, not a code change::

        registries:
          - path: src/omnimarket/configs/routing_tiers.yaml
            list_path: "tiers[].models"
            id_field: id
            disambiguator_field: use_for
          - path: grants/prod_promotion_grants.yaml
            list_path: entries
            id_field: grant_id

``list_path`` syntax:
    - ``"entries"`` — a single flat list of entries to check, resolved by
      dotted key lookup from the file's top-level mapping.
    - ``"tiers[].models"`` — a list of *groups* (``tiers``, dotted-resolved),
      each of which nests its own list of entries (``models``). Uniqueness is
      checked *within* each group independently, never across groups. This
      matters: ``routing_tiers.yaml`` intentionally repeats the same model id
      + same ``use_for`` values across *different* tiers (the same model is a
      legitimate member of more than one rung of the escalation ladder) — only
      a same-tier collision is a real ambiguity.

Disambiguation (``disambiguator_field``, optional):
    Two entries sharing ``id_field`` are tolerated ONLY if a configured
    ``disambiguator_field`` is present on both and its value-sets are disjoint
    (list-valued fields, e.g. ``use_for``, are compared as sets; scalar fields
    as single-element sets). Any overlap, or a missing disambiguator field on
    either side, is a violation. Without a configured ``disambiguator_field``,
    ANY duplicate id is a hard failure — this is the shape of
    ``prod_promotion_grants.yaml``, where ``grant_id`` is documented as a
    unique UUID and has no legitimate disambiguator (unlike ``image_digest``,
    which legitimately repeats across grant re-issuance — that field is
    deliberately NOT the checked id_field for that registry).

Fail-closed: an unparseable registry file, a missing/non-list resolved path,
or an entry missing the configured id_field is a FAILURE, not a skip. A
missing manifest file is not a failure — it means the consuming repo has not
opted any registries into this check yet.

Usage Examples:
    Programmatic usage::

        from pathlib import Path
        from omnibase_core.validation import ValidatorDuplicateConfigIds

        validator = ValidatorDuplicateConfigIds()
        violations = validator.check_manifest(
            Path(".duplicate-id-registries.yaml"), repo_root=Path(".")
        )
        for v in violations:
            print(f"{v.registry_path} [{v.group_label}]: {v.detail}")

    CLI::

        python -m omnibase_core.validation.validator_duplicate_config_ids
        python -m omnibase_core.validation.validator_duplicate_config_ids \\
            --manifest .duplicate-id-registries.yaml --repo-root .

Schema Version:
    v1.0.0 - Initial version
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import OnexError
from omnibase_core.models.validation.model_duplicate_id_check_spec import (
    ModelDuplicateIdCheckSpec,
)
from omnibase_core.models.validation.model_duplicate_id_manifest import (
    ModelDuplicateIdManifest,
)
from omnibase_core.models.validation.model_duplicate_id_violation import (
    ModelDuplicateIdViolation,
)

# ---------------------------------------------------------------------------
# YAML document loading
# ---------------------------------------------------------------------------


def from_yaml_document(path: Path) -> object:
    """Load a registry file's raw YAML document.

    Registry documents have no fixed schema — ``routing_tiers.yaml`` and
    ``prod_promotion_grants.yaml`` have entirely different shapes — so this
    returns the raw parsed value rather than a typed Pydantic model; callers
    narrow it via ``isinstance`` before use.
    """
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Path resolution helpers
# ---------------------------------------------------------------------------


def _get_dotted(data: dict[str, object], dotted_key: str) -> object:
    """Resolve a dotted key path (e.g. ``"a.b.c"``) through nested mappings."""
    cur: object = data
    walked: list[str] = []
    for part in dotted_key.split("."):
        walked.append(part)
        if not isinstance(cur, dict):
            raise OnexError(
                message=f"key path {'.'.join(walked)!r} does not resolve to a mapping",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if part not in cur:
            raise OnexError(
                message=f"key path {'.'.join(walked)!r} not found",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        cur = cur[part]
    return cur


def _split_list_path(list_path: str) -> tuple[str, str | None]:
    """Split a ``list_path`` into (group_key, entry_key).

    ``"entries"`` -> ("entries", None) — no grouping, a single flat list.
    ``"tiers[].models"`` -> ("tiers", "models") — a list of groups, each
    holding its own nested entries list.
    """
    if "[]." in list_path:
        group_key, _, entry_key = list_path.partition("[].")
        if not group_key or not entry_key:
            raise OnexError(
                message=f"malformed list_path: {list_path!r}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return group_key, entry_key
    return list_path, None


def _resolve_groups(
    data: dict[str, object], list_path: str
) -> list[tuple[str | None, list[object]]]:
    """Resolve ``list_path`` against the loaded YAML document into groups.

    Each returned tuple is ``(group_label, entries)``. A flat ``list_path``
    (no ``[].`` marker) produces exactly one group with ``group_label=None``.
    """
    group_key, entry_key = _split_list_path(list_path)

    if entry_key is None:
        entries = _get_dotted(data, group_key)
        if not isinstance(entries, list):
            raise OnexError(
                message=f"{group_key!r} did not resolve to a list",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return [(None, entries)]

    groups_raw = _get_dotted(data, group_key)
    if not isinstance(groups_raw, list):
        raise OnexError(
            message=f"{group_key!r} did not resolve to a list",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    resolved: list[tuple[str | None, list[object]]] = []
    for idx, group in enumerate(groups_raw):
        if not isinstance(group, dict):
            raise OnexError(
                message=f"{group_key}[{idx}] is not a mapping",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        label = str(group.get("name", f"{group_key}[{idx}]"))
        entries = _get_dotted(group, entry_key)
        if not isinstance(entries, list):
            raise OnexError(
                message=f"{group_key}[{idx}].{entry_key} did not resolve to a list",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        resolved.append((label, entries))
    return resolved


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


def _disambiguator_signature(value: object) -> frozenset[object]:
    """Normalize a disambiguator field's value into a comparable set."""
    if isinstance(value, list):
        return frozenset(value)
    return frozenset([value])


def _check_group(
    entries: list[object],
    id_field: str,
    disambiguator_field: str | None,
) -> list[str]:
    """Check one group's entries for duplicate ``id_field`` values.

    Returns human-readable violation strings; an empty list means the group
    is clean. Raises OnexError for structural problems (non-mapping entry,
    missing id_field) — these are fail-closed, not skipped.
    """
    by_id: dict[str, list[int]] = {}
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise OnexError(
                message=f"entry[{idx}] is not a mapping",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if id_field not in entry:
            raise OnexError(
                message=f"entry[{idx}] is missing required id field {id_field!r}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        by_id.setdefault(str(entry[id_field]), []).append(idx)

    violations: list[str] = []
    for id_value, idxs in by_id.items():
        if len(idxs) < 2:
            continue

        if disambiguator_field is None:
            violations.append(
                f"duplicate {id_field}={id_value!r} across {len(idxs)} entries "
                f"(indices {idxs}); no disambiguator_field configured for this "
                f"registry — every {id_field} must be unique"
            )
            continue

        signatures: list[frozenset[object] | None] = []
        for i in idxs:
            entry = entries[i]
            assert isinstance(entry, dict)  # narrowed above
            if disambiguator_field not in entry:
                violations.append(
                    f"duplicate {id_field}={id_value!r}: entry[{i}] is missing "
                    f"disambiguator field {disambiguator_field!r}"
                )
                signatures.append(None)
                continue
            signatures.append(_disambiguator_signature(entry[disambiguator_field]))

        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                sig_a, sig_b = signatures[a], signatures[b]
                if sig_a is None or sig_b is None:
                    continue  # already flagged above
                overlap = sig_a & sig_b
                if overlap:
                    violations.append(
                        f"duplicate {id_field}={id_value!r}: entry[{idxs[a]}] and "
                        f"entry[{idxs[b]}] both declare {disambiguator_field}="
                        f"{sorted(overlap, key=str)!r} — ambiguous which wins"
                    )
    return violations


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class ValidatorDuplicateConfigIds(BaseModel):
    """Reject config/registry files declaring duplicate ids over a non-unique key.

    Stateless: each call returns violations without mutating instance state.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    def check_registry(
        self, spec: ModelDuplicateIdCheckSpec, repo_root: Path
    ) -> list[ModelDuplicateIdViolation]:
        """Check a single registry file against its spec."""
        file_path = repo_root / spec.path
        if not file_path.is_file():
            return [
                ModelDuplicateIdViolation(
                    registry_path=spec.path,
                    group_label=None,
                    detail=f"registry file not found: {file_path}",
                )
            ]

        try:
            data = from_yaml_document(file_path)
        except yaml.YAMLError as exc:
            return [
                ModelDuplicateIdViolation(
                    registry_path=spec.path,
                    group_label=None,
                    detail=f"unparseable YAML: {exc}",
                )
            ]

        if not isinstance(data, dict):
            return [
                ModelDuplicateIdViolation(
                    registry_path=spec.path,
                    group_label=None,
                    detail="top-level YAML content must be a mapping",
                )
            ]

        try:
            groups = _resolve_groups(data, spec.list_path)
        except OnexError as exc:
            return [
                ModelDuplicateIdViolation(
                    registry_path=spec.path, group_label=None, detail=str(exc)
                )
            ]

        violations: list[ModelDuplicateIdViolation] = []
        for label, entries in groups:
            try:
                details = _check_group(entries, spec.id_field, spec.disambiguator_field)
            except OnexError as exc:
                violations.append(
                    ModelDuplicateIdViolation(
                        registry_path=spec.path, group_label=label, detail=str(exc)
                    )
                )
                continue
            violations.extend(
                ModelDuplicateIdViolation(
                    registry_path=spec.path, group_label=label, detail=d
                )
                for d in details
            )
        return violations

    def check_manifest(
        self, manifest_path: Path, repo_root: Path
    ) -> list[ModelDuplicateIdViolation]:
        """Check every registry declared in the manifest. Raises OnexError on a malformed manifest."""
        manifest = ModelDuplicateIdManifest.from_yaml(manifest_path)
        violations: list[ModelDuplicateIdViolation] = []
        for spec in manifest.registries:
            violations.extend(self.check_registry(spec, repo_root))
        return violations


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint.

    Exit codes:
        0 — no violations (including: no manifest declared yet)
        1 — violations found, or the manifest itself is malformed
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="check-duplicate-registry-ids",
        description=(
            "Reject config/registry YAML files declaring duplicate ids over a "
            "key that is not guaranteed unique. Checked registries are declared "
            "config-as-data in a manifest file."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(".duplicate-id-registries.yaml"),
        help="Path to the manifest file (default: .duplicate-id-registries.yaml)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(),
        help="Root directory registry paths in the manifest are relative to (default: cwd)",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Ignored — accepted for pre-commit pass_filenames compatibility",
    )
    parsed = parser.parse_args(argv)

    if not parsed.manifest.is_file():
        print(
            f"No manifest at {parsed.manifest} — no registries opted in, nothing to check."
        )
        return 0

    validator = ValidatorDuplicateConfigIds()
    try:
        violations = validator.check_manifest(parsed.manifest, parsed.repo_root)
    except OnexError as exc:
        print(f"FAIL: cannot load manifest {parsed.manifest}: {exc}")
        return 1

    for v in violations:
        label = f" [group={v.group_label}]" if v.group_label else ""
        print(f"{v.registry_path}{label}: {v.detail}")

    if violations:
        print(f"\n{len(violations)} duplicate-id registry violation(s).")
        return 1

    print("No duplicate-id registry violations found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
