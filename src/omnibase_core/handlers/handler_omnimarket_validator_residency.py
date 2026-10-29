# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validator-residency checker (OMN-21503, plan task T-Q6).

Counts the validator predicates resident in a consuming repository against a
shrink-only baseline, and holds the inventory of those validators to the files.

Pure: a listing of repository-relative paths, the scan policy, the inventory and
the baselines come in as typed facts, a result with ``ModelValidationIssue``
items goes out, nothing is read from disk. Every path glob, directory and name
pattern arrives in ``policy`` from the validator's ``.validation.yaml``
contract; this module holds none of them.

Residents are scripts matching ``policy.script_globs`` and node directories
under ``policy.node_root`` whose name fullmatches one of
``policy.node_name_patterns``. A resident the inventory classes as a decision
or as other is not counted; a resident the inventory does not list is counted
(it is an unclassified validator until a person classes it).
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Mapping, Sequence

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_validator_inventory_class import (
    EnumValidatorInventoryClass,
)
from omnibase_core.enums.enum_validator_inventory_kind import (
    EnumValidatorInventoryKind,
)
from omnibase_core.handlers.handler_shrink_only_baseline import (
    compare_shrink_only,
    verdict_issues,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_omnimarket_validator_inventory_entry import (
    ModelOmnimarketValidatorInventoryEntry,
)
from omnibase_core.models.validation.model_omnimarket_validator_residency_policy import (
    ModelOmnimarketValidatorResidencyPolicy,
)
from omnibase_core.models.validation.model_omnimarket_validator_residency_result import (
    ModelOmnimarketValidatorResidencyResult,
)

__all__ = [
    "ModelOmnimarketValidatorResidencyResult",
    "check_validator_residency",
    "check_wave_acceptance",
    "discover_residents",
]

_RULE = "validator_residency"
_KIND_RATCHET = "validator_residency"


def discover_residents(
    tree_paths: Sequence[str], policy: ModelOmnimarketValidatorResidencyPolicy
) -> tuple[tuple[str, EnumValidatorInventoryKind], ...]:
    """Resident ids and kinds in the listing, sorted by id."""
    found: dict[str, EnumValidatorInventoryKind] = {}
    name_patterns = tuple(re.compile(p) for p in policy.node_name_patterns)
    root_prefix = policy.node_root.rstrip("/") + "/"
    for raw in tree_paths:
        path = raw.replace("\\", "/")
        if any(fnmatch.fnmatchcase(path, glob) for glob in policy.script_globs):
            found[path] = EnumValidatorInventoryKind.SCRIPT
        if path.startswith(root_prefix):
            rest = path[len(root_prefix) :]
            name, separator, _ = rest.partition("/")
            if separator and any(p.fullmatch(name) for p in name_patterns):
                found[root_prefix + name] = EnumValidatorInventoryKind.NODE
    return tuple(sorted(found.items()))


def _issue(
    severity: EnumSeverity, code: str, message: str, subject: str | None = None
) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=severity,
        message=message,
        code=code,
        rule_name=_RULE,
        context={"subject": subject} if subject is not None else None,
    )


def check_validator_residency(
    *,
    tree_paths: Sequence[str],
    policy: ModelOmnimarketValidatorResidencyPolicy,
    inventory: Sequence[ModelOmnimarketValidatorInventoryEntry],
    baseline_ids: Sequence[str],
    previous_baseline_ids: Sequence[str] | None = None,
) -> ModelOmnimarketValidatorResidencyResult:
    """Judge a listing against the inventory and the shrink-only baseline."""
    residents = dict(discover_residents(tree_paths, policy))
    by_id = {entry.path: entry for entry in inventory}
    issues: list[ModelValidationIssue] = []

    unclassified = tuple(sorted(rid for rid in residents if rid not in by_id))
    for rid in unclassified:
        issues.append(
            _issue(
                EnumSeverity.ERROR,
                "inventory_unclassified",
                f"{rid} is resident but not in the validator inventory; class it "
                "and name its replacing core validator, or do not add it",
                rid,
            )
        )
    for entry in sorted(inventory, key=lambda e: e.path):
        if entry.path not in residents:
            issues.append(
                _issue(
                    EnumSeverity.ERROR,
                    "inventory_stale",
                    f"{entry.path} is in the inventory but no longer resident; "
                    "remove the entry",
                    entry.path,
                )
            )
            continue
        if entry.validator_class is not EnumValidatorInventoryClass.VALIDATOR:
            continue
        if entry.replacing_core_validator is None:
            issues.append(
                _issue(
                    EnumSeverity.ERROR,
                    "inventory_no_replacement",
                    f"{entry.path} is classed a validator with no replacing core "
                    "validator",
                    entry.path,
                )
            )
        if entry.child_ticket is None:
            issues.append(
                _issue(
                    policy.child_ticket_severity,
                    "inventory_no_child_ticket",
                    f"{entry.path} is classed a validator with no child ticket",
                    entry.path,
                )
            )

    counted = tuple(
        sorted(
            rid
            for rid in residents
            if rid not in by_id
            or by_id[rid].validator_class is EnumValidatorInventoryClass.VALIDATOR
        )
    )
    verdict = compare_shrink_only(
        _KIND_RATCHET, counted, baseline_ids, previous_baseline_ids
    )
    issues.extend(verdict_issues(verdict))

    return ModelOmnimarketValidatorResidencyResult(
        resident_validators=counted,
        count=len(counted),
        unclassified=unclassified,
        issues=tuple(sorted(issues, key=_issue_key)),
    )


def _issue_key(issue: ModelValidationIssue) -> tuple[str, str, str]:
    subject = (issue.context or {}).get("subject", "")
    return (issue.code or "", subject, issue.message)


def check_wave_acceptance(
    *,
    manifest: Mapping[str, object],
    baseline_ids: Sequence[str],
    policy: ModelOmnimarketValidatorResidencyPolicy,
) -> tuple[ModelValidationIssue, ...]:
    """Reject the acceptance wave while a resident validator remains.

    ``manifest`` is the parsed wave manifest: ``waves`` maps a wave number to a
    mapping whose ``obligations`` list must carry ``policy.wave_obligation``.
    The obligation is the committed baseline at zero, so a nonzero baseline
    rejects the wave.
    """
    waves = manifest.get("waves")
    wave = (
        waves.get(str(policy.acceptance_wave)) if isinstance(waves, Mapping) else None
    )
    obligations = wave.get("obligations") if isinstance(wave, Mapping) else None
    declared = (
        isinstance(obligations, Sequence) and policy.wave_obligation in obligations
    )
    issues: list[ModelValidationIssue] = []
    if not declared:
        issues.append(
            _issue(
                EnumSeverity.ERROR,
                "wave_obligation_missing",
                f"wave {policy.acceptance_wave} does not carry the obligation "
                f"{policy.wave_obligation}",
            )
        )
    if baseline_ids:
        issues.append(
            _issue(
                EnumSeverity.ERROR,
                "wave_baseline_nonzero",
                f"wave {policy.acceptance_wave} is rejected: the validator "
                f"baseline holds {len(baseline_ids)} resident validator(s), "
                "it must be at zero",
            )
        )
    return tuple(issues)
