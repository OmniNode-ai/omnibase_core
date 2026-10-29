# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker_delivery_reference: classify and judge delivered artifact reads.

All delivery policy comes from the delivery_paths overlay. The change source
supplies resolution facts; this module performs no I/O.
"""

from __future__ import annotations

import re
from fnmatch import fnmatch
from typing import Final

from omnibase_core.enums.enum_delivery_reference_kind import EnumDeliveryReferenceKind
from omnibase_core.enums.enum_delivery_resolved_kind import EnumDeliveryResolvedKind
from omnibase_core.enums.enum_delivery_status import EnumDeliveryStatus
from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.delivery import (
    ModelDeliveryFacts,
    ModelDeliveryFile,
    ModelDeliveryIssue,
    ModelDeliveryOverlay,
    ModelDeliveryPath,
    ModelDeliveryRef,
)

__all__ = [
    "classify_reference",
    "judge_reference",
    "check_delivery_paths",
    "reconcile_consumers",
    "discover_references",
    "to_validation_issues",
]

_FULL_OBJECT_ID: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


def classify_reference(
    ref: ModelDeliveryRef, path: ModelDeliveryPath | None, overlay: ModelDeliveryOverlay
) -> EnumDeliveryReferenceKind:
    """Classify in precedence order using supplied resolution and overlay data."""
    text = ref.reference_text.strip()
    if not text:
        return EnumDeliveryReferenceKind.UNKNOWN
    names = (text, *ref.automation_names)
    declared = tuple(
        name
        for name in names
        if any(re.search(m.pattern, name) for m in overlay.dependency_mechanisms)
    )
    if any(
        re.search(pattern, name)
        for name in names
        if name not in declared
        for pattern in overlay.bump_automation_patterns
    ):
        return EnumDeliveryReferenceKind.BUMP_PR
    if declared:
        return EnumDeliveryReferenceKind.DECLARED_DEPENDENCY_PIN
    if ref.resolved_kind == EnumDeliveryResolvedKind.BRANCH:
        return EnumDeliveryReferenceKind.BRANCH
    if (
        _FULL_OBJECT_ID.fullmatch(text)
        or ref.resolved_kind == EnumDeliveryResolvedKind.COMMIT
    ):
        if path is not None and path.bootstrap_pin == text:
            return EnumDeliveryReferenceKind.GATE_BOOTSTRAP_PIN
        return EnumDeliveryReferenceKind.SHA
    if ref.resolved_kind == EnumDeliveryResolvedKind.TAG:
        if (
            ref.consumer_kind in overlay.reusable_workflow_consumer_kinds
            and not ref.runtime_resolution
        ):
            return EnumDeliveryReferenceKind.HAND_KEPT_VERSION
        if re.fullmatch(overlay.tag_pattern, text):
            return EnumDeliveryReferenceKind.DEV_MERGE_TAG
        if overlay.candidate_tag_pattern is not None and re.fullmatch(
            overlay.candidate_tag_pattern, text
        ):
            return EnumDeliveryReferenceKind.CANDIDATE_TAG
        return EnumDeliveryReferenceKind.HAND_KEPT_VERSION
    if ref.resolved_kind == EnumDeliveryResolvedKind.VERSION:
        return EnumDeliveryReferenceKind.HAND_KEPT_VERSION
    return EnumDeliveryReferenceKind.UNKNOWN


def _issue(
    path_name: str | None,
    location: str,
    consumer_kind: str,
    kind: EnumDeliveryReferenceKind,
    status: EnumDeliveryStatus,
    reason: str,
) -> ModelDeliveryIssue:
    return ModelDeliveryIssue(
        path_name=path_name,
        location=location,
        consumer_kind=consumer_kind,
        kind=kind,
        status=status,
        reference_allowed=status == EnumDeliveryStatus.ALLOWED,
        reason=reason,
        message=f"{location}: {kind.value} {status.value}: {reason}",
    )


def judge_reference(
    ref: ModelDeliveryRef, path: ModelDeliveryPath, overlay: ModelDeliveryOverlay
) -> ModelDeliveryIssue:
    """Apply the declared role permission, immutability and binding checks."""
    kind = classify_reference(ref, path, overlay)
    status = EnumDeliveryStatus.REFUSED
    if (
        ref.consumer_kind not in overlay.consumer_kinds
        or path.consumer_kind not in overlay.consumer_kinds
    ):
        reason = "unlisted_consumer_kind"
    elif (
        kind
        in (
            EnumDeliveryReferenceKind.DEV_MERGE_TAG,
            EnumDeliveryReferenceKind.CANDIDATE_TAG,
        )
        and ref.first_resolved_target
        and ref.resolved_target
        and ref.first_resolved_target != ref.resolved_target
    ):
        status = EnumDeliveryStatus.TAG_MOVED
        reason = "tag_target_changed"
    else:
        kinds = next(
            (
                permission.kinds
                for permission in overlay.role_permissions
                if permission.role == path.role
            ),
            (),
        )
        if kind == EnumDeliveryReferenceKind.UNKNOWN or kind not in kinds:
            reason = "kind_not_permitted_for_role"
        elif kind == EnumDeliveryReferenceKind.CANDIDATE_TAG and not all(
            (
                ref.candidate_pr_head,
                ref.candidate_test_merge_target,
                ref.candidate_artifact_digest,
            )
        ):
            reason = "candidate_not_bound"
        elif (
            kind == EnumDeliveryReferenceKind.GATE_BOOTSTRAP_PIN
            and not ref.runtime_resolution
        ):
            reason = "bootstrap_without_runtime_resolution"
        else:
            status = EnumDeliveryStatus.ALLOWED
            reason = "permitted"
    return _issue(path.path_name, ref.location, ref.consumer_kind, kind, status, reason)


def check_delivery_paths(facts: ModelDeliveryFacts) -> tuple[ModelDeliveryIssue, ...]:
    """Judge every read of each declared path (a path with none is blocked), then report unjoined references."""
    issues: list[ModelDeliveryIssue] = []
    declared = {path.path_name for path in facts.paths}
    for path in facts.paths:
        observed = [ref for ref in facts.refs if ref.path_name == path.path_name]
        if not observed:
            issues.append(
                _issue(
                    path.path_name,
                    path.location,
                    path.consumer_kind,
                    EnumDeliveryReferenceKind.UNKNOWN,
                    EnumDeliveryStatus.BLOCKED,
                    "no_reference_read",
                )
            )
        issues.extend(judge_reference(ref, path, facts.overlay) for ref in observed)
    issues.extend(
        _issue(
            ref.path_name,
            ref.location,
            ref.consumer_kind,
            classify_reference(ref, None, facts.overlay),
            EnumDeliveryStatus.UNDECLARED,
            "consumer_not_declared",
        )
        for ref in facts.refs
        if ref.path_name not in declared
    )
    return tuple(issues)


def reconcile_consumers(facts: ModelDeliveryFacts) -> tuple[ModelDeliveryIssue, ...]:
    """Report unreadable declarations, undeclared discoveries, and refused discoveries at declared locations."""
    issues = [
        _issue(
            path.path_name,
            path.location,
            path.consumer_kind,
            EnumDeliveryReferenceKind.UNKNOWN,
            EnumDeliveryStatus.BLOCKED,
            "declaration_unreadable",
        )
        for path in facts.paths
        if path.location in facts.unreadable_locations
    ]
    by_location = {path.location: path for path in facts.paths}
    undeclared = sorted(
        (ref for ref in facts.discovered if ref.location not in by_location),
        key=lambda ref: (ref.location, ref.line_number or 0, ref.reference_text),
    )
    issues.extend(
        _issue(
            ref.path_name,
            ref.location,
            ref.consumer_kind,
            classify_reference(ref, None, facts.overlay),
            EnumDeliveryStatus.UNDECLARED,
            "consumer_not_declared",
        )
        for ref in undeclared
    )
    judged = (
        judge_reference(ref, by_location[ref.location], facts.overlay)
        for ref in facts.discovered
        if ref.location in by_location
    )
    issues.extend(issue for issue in judged if not issue.reference_allowed)
    return tuple(issues)


def discover_references(
    files: tuple[ModelDeliveryFile, ...], overlay: ModelDeliveryOverlay
) -> tuple[ModelDeliveryRef, ...]:
    """Extract unresolved references from text with overlay discovery patterns."""
    found: list[ModelDeliveryRef] = []
    for file in files:
        for pattern in overlay.discovery_patterns:
            if not fnmatch(file.location, pattern.file_pattern):
                continue
            for number, line in enumerate(file.text.splitlines(), start=1):
                for match in re.finditer(pattern.reference_pattern, line):
                    found.append(
                        ModelDeliveryRef(
                            path_name=None,
                            location=file.location,
                            consumer_kind=pattern.consumer_kind,
                            reference_text=match.group("ref"),
                            resolved_kind=EnumDeliveryResolvedKind.UNRESOLVED,
                            line_number=number,
                        )
                    )
    return tuple(found)


def to_validation_issues(
    issues: tuple[ModelDeliveryIssue, ...],
) -> tuple[ModelValidationIssue, ...]:
    """Map non-allowed verdicts to the shared validation reporting model."""
    return tuple(
        ModelValidationIssue(
            severity=EnumSeverity.ERROR,
            message=issue.message,
            code=issue.status.value,
            rule_name=f"delivery_reference_{issue.status.value}",
            context={
                "path_name": issue.path_name or "",
                "location": issue.location,
                "kind": issue.kind.value,
                "reason": issue.reason,
            },
        )
        for issue in issues
        if not issue.reference_allowed
    )
