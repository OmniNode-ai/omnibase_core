# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic OCC-first merge eligibility checks.

This module is intentionally pure after the caller supplies a PR metadata
snapshot and a pinned OCC commit SHA. It does not fetch GitHub or mutate state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse
from uuid import UUID

import yaml
from pydantic import ValidationError

from omnibase_core.crypto.crypto_ed25519_signer import verify_base64
from omnibase_core.enums.enum_goal_attempt_status import EnumGoalAttemptStatus
from omnibase_core.enums.enum_occ_eligibility_reason import EnumOccEligibilityReason
from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.errors.error_goal_admission_provider import (
    GoalAdmissionProviderError,
)
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.ticket.model_dod_evidence_check import (
    ModelDodEvidenceCheck,
)
from omnibase_core.models.contracts.ticket.model_dod_evidence_item import (
    ModelDodEvidenceItem,
)
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem
from omnibase_core.models.validation.model_goal_admission_observation import (
    ModelGoalAdmissionObservation,
)
from omnibase_core.models.validation.model_goal_attempt_allocation_snapshot import (
    ModelGoalAttemptAllocationSnapshot,
)
from omnibase_core.models.validation.model_goal_criterion_baseline import (
    ModelGoalCriterionBaseline,
)
from omnibase_core.models.validation.model_goal_evaluation_observation import (
    ModelGoalEvaluationObservation,
)
from omnibase_core.models.validation.model_goal_execution_result import (
    ModelGoalExecutionResult,
)
from omnibase_core.models.validation.model_goal_fork_resolution_record import (
    ModelGoalForkResolutionRecord,
)
from omnibase_core.models.validation.model_goal_mutation_state import (
    ModelGoalMutationState,
)
from omnibase_core.models.validation.model_goal_revision_history_snapshot import (
    ModelGoalRevisionHistorySnapshot,
)
from omnibase_core.models.validation.model_goal_subject_manifest import (
    ModelGoalSubjectManifest,
)
from omnibase_core.models.validation.model_goal_supervisor_attestation import (
    ModelGoalSupervisorAttestation,
)
from omnibase_core.models.validation.model_goal_supervisor_execution_receipt import (
    ModelGoalSupervisorExecutionReceipt,
)
from omnibase_core.models.validation.model_goal_verification_attempt import (
    ModelGoalVerificationAttempt,
)
from omnibase_core.models.validation.model_goal_verifier_policy import (
    ModelGoalVerifierPolicy,
)
from omnibase_core.models.validation.model_occ_eligibility_input import (
    ModelOccEligibilityInput,
)
from omnibase_core.models.validation.model_occ_eligibility_result import (
    ModelOccEligibilityResult,
)
from omnibase_core.utils.util_goal_verification import (
    compute_goal_execution_request_sha256,
)
from omnibase_core.validation.protocol_goal_admission_provider import (
    ProtocolGoalAdmissionProvider,
)
from omnibase_core.validation.validator_receipt_gate import (
    _CONTRACT_SHA256_REQUIRED_AFTER,
    _extract_ticket_ids,
    _honestly_superseded_dod_ids,
    _iter_dod_evidence,
    check_receipt_contract_binding,
    compute_canonical_contract_sha256,
)
from omnibase_core.validation.validator_receipt_supersession import (
    resolve_supersession,
)

EVIDENCE_TICKET_PATTERN = re.compile(
    r"^\s*Evidence-Ticket\s*:\s*(OMN-\d+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
TICKET_TOKEN_PATTERN = re.compile(r"(?<![A-Z0-9])OMN-(\d+)(?![A-Z0-9])", re.IGNORECASE)

# OMN-16353: the OCC evidence repo, where a PR under evaluation is itself the
# companion carrying contracts/receipts and must self-bind via an
# `occ-self-bind-pr-<N>` entry. Callers pass either the short repo name (the
# CI workflows pass `REPO_SHORT`) or the org-qualified form.
_OCC_REPO_NAME = "onex_change_control"
_OCC_REPO_ORG = "OmniNode-ai"
_OCC_REPO_QUALIFIED = f"{_OCC_REPO_ORG}/{_OCC_REPO_NAME}"
_STRUCTURAL_BINDINGS_RELATIVE_DIR = Path("drift/occ_bindings")
_STRUCTURAL_SELF_BIND_CHECK_TYPE = "command"

# OMN-16859: check types a PRODUCT-REPO CI runner executes and supersedes.
#
# The OCC companion producers (`OccCompanionEmitter` born path,
# `node_occ_companion_compute`) run inside the .201 dev-lane effects runtime,
# which holds no product-repo checkout — the declared `cwd` is
# `${OMNI_HOME}/<repo>`, a path that does not exist there. They therefore
# cannot execute a `test_passes` check, and the honest mint is a PENDING
# receipt ("the probe was allocated but has not yet executed", per
# `EnumReceiptStatus`) rather than a PASS behind a `gh pr view` probe.
#
# The surface that CAN execute it honestly is the product repo's own CI, which
# has the checkout, the dependencies and the real test targets. It writes the
# executed result into the OPEN companion branch as a net-new supersession
# record, which `resolve_supersession` re-binds this key to.
#
# Membership here changes only the REASON reported while that is outstanding.
# It never makes a PR eligible. Keep this set to types a runner genuinely
# covers: adding a type with no runner behind it would turn a permanent block
# into a message claiming something is on its way when nothing is.
RUNNER_COVERED_CHECK_TYPES = frozenset({"test_passes"})


def _is_occ_repo(repo: str) -> bool:
    """True only for the canonical OCC repo — bare name or exact org/name.

    Matches the short name (``onex_change_control``, what CI passes as
    ``REPO_SHORT``) or the exact canonical org-qualified name
    (``OmniNode-ai/onex_change_control``). Deliberately NOT a bare suffix
    match: a differently-owned repo that merely shares the short name (e.g.
    a fork under another org) must not be classified as the OCC evidence
    repo (CodeRabbit finding on OMN-16353's initial diff).
    """
    normalized = repo.strip().rstrip("/")
    return normalized in (_OCC_REPO_NAME, _OCC_REPO_QUALIFIED)


def _self_bind_remediation(ticket_id: str, pr_number: int) -> str:
    """Exact remedy for an OCC companion missing its self-bind (OMN-16353).

    Emitted only when everything else verifies: contracts resolve, receipts
    are PASS and hash-bound — the sole defect is that no receipt carries
    ``pr_number == <this OCC PR>``. Names the precise YAML entry and receipt
    path so the convention is taught at the moment of failure instead of
    costing a full CI round-trip of re-diagnosis.
    """
    evidence_id = f"occ-self-bind-pr-{pr_number}"
    return (
        f"OCC evidence for {ticket_id} verifies (receipts PASS, hashes bound), "
        f"but no structural receipt binds to this OCC PR (#{pr_number}). "
        "Mint a PASS structural binding receipt at "
        f"drift/occ_bindings/{ticket_id}/{evidence_id}/command.yaml with "
        f"ticket_id: {ticket_id}, evidence_item_id: {evidence_id}, "
        f"check_type: {_STRUCTURAL_SELF_BIND_CHECK_TYPE}, pr_number: {pr_number}, "
        "and contract_sha256 equal to the current ticket contract hash. "
        "Do not declare this structural receipt in dod_evidence, do not add "
        "binds_ac, and do not mint contract_entry_sha256 for an undeclared item "
        "(OMN-18075)."
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _load_yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as fh:
        return yaml.load(fh, Loader=yaml.SafeLoader)


def _normalize_sha_set(values: tuple[str, ...]) -> set[str]:
    return {v.strip().lower() for v in values if v.strip()}


def _ticket_bound_to_pr(ticket_id: str, snapshot: ModelOccEligibilityInput) -> bool:
    searchable_texts = (
        snapshot.pr_title,
        snapshot.pr_branch,
        *snapshot.pr_commit_texts,
    )
    bound_tickets = {
        f"OMN-{match.group(1)}".upper()
        for text in searchable_texts
        for match in TICKET_TOKEN_PATTERN.finditer(text)
    }
    evidence_tickets = {
        match.group(1).upper()
        for match in EVIDENCE_TICKET_PATTERN.finditer(snapshot.pr_body)
    }
    return ticket_id in bound_tickets or ticket_id in evidence_tickets


def _receipt_bound_to_pr(
    receipt: ModelDodReceipt,
    snapshot: ModelOccEligibilityInput,
) -> bool:
    if receipt.pr_number == snapshot.pr_number:
        return True
    shas = _normalize_sha_set(snapshot.pr_commit_shas)
    return receipt.commit_sha.lower() in shas


class _DuplicateKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects ambiguous duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _DuplicateKeySafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = cast(Any, loader).construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = cast(Any, loader).construct_object(value_node, deep=deep)
    return mapping


_DuplicateKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _goal_result(
    snapshot: ModelOccEligibilityInput,
    *,
    allocation: ModelGoalAttemptAllocationSnapshot | None,
    eligible: bool,
    reason: EnumOccEligibilityReason,
    detail: str,
    contract_hashes: dict[str, str] | None = None,
    receipt_ids: tuple[str, ...] = (),
    missing: tuple[str, ...] = (),
    stale: tuple[str, ...] = (),
    goal_revision_history_sha256: str | None = None,
    goal_policy_revision: UUID | None = None,
    goal_revision_history_store_revision: UUID | None = None,
    criterion_baseline_sha256: str | None = None,
    criterion_coverage_sha256: str | None = None,
    evaluation_observation: ModelGoalEvaluationObservation | None = None,
    admission_observation: ModelGoalAdmissionObservation | None = None,
    dependency_admission_observation_refs: dict[str, tuple[UUID, str]] | None = None,
    mutation_state: ModelGoalMutationState | None = None,
) -> ModelOccEligibilityResult:
    """Build a goal verdict with its explicit source/subject provenance."""
    assert snapshot.goal_id is not None
    assert snapshot.contract_revision is not None
    assert snapshot.contract_schema_version is not None
    assert snapshot.goal_contract_path is not None
    assert snapshot.goal_contract_source_commit_sha is not None
    assert snapshot.goal_contract_sha256 is not None
    assert snapshot.subject_commit_sha is not None
    assert snapshot.subject_tree_sha is not None
    selected_attempt: ModelGoalVerificationAttempt | None = None
    if allocation is not None and allocation.attempts:
        selected_attempt = max(
            allocation.attempts,
            key=lambda item: item.sequence,
        )
    return ModelOccEligibilityResult(
        eligible=eligible,
        reason=reason,
        ticket_ids=(snapshot.goal_ticket_id,) if snapshot.goal_ticket_id else (),
        occ_commit_sha=snapshot.occ_commit_sha,
        contract_hashes=contract_hashes or {},
        receipt_ids=receipt_ids,
        missing_or_nonpass_receipts=missing,
        stale_receipt_bindings=stale,
        detail=detail,
        goal_id=snapshot.goal_id,
        repository=snapshot.repo,
        contract_revision=snapshot.contract_revision,
        contract_schema_version=snapshot.contract_schema_version,
        goal_contract_path=snapshot.goal_contract_path,
        goal_contract_source_commit_sha=snapshot.goal_contract_source_commit_sha,
        goal_contract_sha256=snapshot.goal_contract_sha256,
        subject_commit_sha=snapshot.subject_commit_sha,
        subject_tree_sha=snapshot.subject_tree_sha,
        attempt_id=selected_attempt.attempt_id if selected_attempt else None,
        attempt_sequence=selected_attempt.sequence if selected_attempt else None,
        attempt_watermark_sequence=(
            allocation.watermark_sequence if allocation else None
        ),
        attempt_store_revision=(allocation.store_revision if allocation else None),
        attempt_snapshot_sha256=(allocation.snapshot_sha256 if allocation else None),
        goal_revision_history_sha256=goal_revision_history_sha256,
        goal_policy_revision=goal_policy_revision,
        goal_revision_history_store_revision=goal_revision_history_store_revision,
        criterion_baseline_sha256=criterion_baseline_sha256,
        criterion_coverage_sha256=criterion_coverage_sha256,
        evaluation_observation_id=(
            evaluation_observation.observation_id
            if evaluation_observation is not None
            else None
        ),
        deadline_event_id=(
            evaluation_observation.deadline_event_id
            if evaluation_observation is not None
            else None
        ),
        evaluation_observed_at=(
            evaluation_observation.observed_at
            if evaluation_observation is not None
            else None
        ),
        evaluation_observation_sha256=(
            evaluation_observation.content_sha256()
            if evaluation_observation is not None
            else None
        ),
        admission_observation_id=(
            admission_observation.observation_id
            if admission_observation is not None
            else None
        ),
        admission_observation_sha256=(
            admission_observation.content_sha256()
            if admission_observation is not None
            else None
        ),
        dependency_admission_observation_refs=(
            dependency_admission_observation_refs or {}
        ),
        evaluation_deadline_status=(
            evaluation_observation.deadline_status
            if evaluation_observation is not None
            else None
        ),
        evaluation_deadline_recorded_at=(
            evaluation_observation.deadline_recorded_at
            if evaluation_observation is not None
            else None
        ),
        evaluation_subject_kind=(
            evaluation_observation.subject_kind
            if evaluation_observation is not None
            else None
        ),
        evaluation_commit_source=(
            evaluation_observation.commit_source
            if evaluation_observation is not None
            else None
        ),
        evaluation_subject_ref=(
            evaluation_observation.subject_ref
            if evaluation_observation is not None
            else None
        ),
        evaluation_subject_repository=(
            evaluation_observation.subject_repository
            if evaluation_observation is not None
            else None
        ),
        evaluation_pull_request_number=(
            evaluation_observation.pull_request_number
            if evaluation_observation is not None
            else None
        ),
        evaluation_base_repository=(
            evaluation_observation.base_repository
            if evaluation_observation is not None
            else None
        ),
        evaluation_base_ref=(
            evaluation_observation.base_ref
            if evaluation_observation is not None
            else None
        ),
        evaluation_merge_group_id=(
            evaluation_observation.merge_group_id
            if evaluation_observation is not None
            else None
        ),
        evaluation_merge_group_base_sha=(
            evaluation_observation.merge_group_base_sha
            if evaluation_observation is not None
            else None
        ),
        evaluation_merge_group_base_tree_sha=(
            evaluation_observation.merge_group_base_tree_sha
            if evaluation_observation is not None
            else None
        ),
        evaluation_merge_group_head_sha=(
            evaluation_observation.merge_group_head_sha
            if evaluation_observation is not None
            else None
        ),
        evaluation_merge_group_head_tree_sha=(
            evaluation_observation.merge_group_head_tree_sha
            if evaluation_observation is not None
            else None
        ),
        evaluation_merge_group_delivery_id=(
            evaluation_observation.merge_group_delivery_id
            if evaluation_observation is not None
            else None
        ),
        evaluation_merge_group_ref=(
            evaluation_observation.merge_group_ref
            if evaluation_observation is not None
            else None
        ),
        evaluation_merge_group_base_ref=(
            evaluation_observation.merge_group_base_ref
            if evaluation_observation is not None
            else None
        ),
        evaluation_merge_group_head_ref=(
            evaluation_observation.merge_group_head_ref
            if evaluation_observation is not None
            else None
        ),
        evaluation_merge_group_source_checkpoint_id=(
            evaluation_observation.merge_group_source_checkpoint_id
            if evaluation_observation is not None
            else None
        ),
        evaluation_merge_group_source_body_sha256=(
            evaluation_observation.merge_group_source_body_sha256
            if evaluation_observation is not None
            else None
        ),
        evaluation_merge_group_received_at=(
            evaluation_observation.merge_group_received_at
            if evaluation_observation is not None
            else None
        ),
        evaluation_deployment_id=(
            evaluation_observation.deployment_id
            if evaluation_observation is not None
            else None
        ),
        evaluation_environment_id=(
            evaluation_observation.environment_id
            if evaluation_observation is not None
            else None
        ),
        evaluation_runtime_instance_id=(
            evaluation_observation.runtime_instance_id
            if evaluation_observation is not None
            else None
        ),
        evaluation_artifact_sha256=(
            evaluation_observation.artifact_sha256
            if evaluation_observation is not None
            else None
        ),
        evaluation_runtime_config_sha256=(
            evaluation_observation.runtime_config_sha256
            if evaluation_observation is not None
            else None
        ),
        goal_mutation_store_revision=(
            mutation_state.store_revision if mutation_state is not None else None
        ),
        goal_mutation_state_sha256=(
            mutation_state.content_sha256() if mutation_state is not None else None
        ),
        goal_mutation_intent_id=(
            mutation_state.intent.intent_id
            if mutation_state is not None and mutation_state.intent is not None
            else None
        ),
    )


def _git(
    repository: Path,
    *arguments: str,
    timeout_seconds: float = 10.0,
) -> subprocess.CompletedProcess[bytes]:
    """Run a bounded Git read using an argument vector, never a shell."""
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=False,
        capture_output=True,
        timeout=timeout_seconds,
    )


def _remote_repository(remote: str) -> str | None:
    """Extract owner/repository from an HTTPS or SSH Git remote URL."""
    if remote.startswith("git@github.com:"):
        path = remote.split(":", 1)[1]
    else:
        parsed = urlparse(remote)
        if parsed.scheme not in {"https", "ssh", "git"}:
            return None
        if parsed.hostname not in {"github.com", "www.github.com"}:
            return None
        path = parsed.path.lstrip("/")
    path = path.removesuffix(".git").strip("/")
    parts = path.split("/")
    if len(parts) != 2 or not all(parts):
        return None
    return f"{parts[0]}/{parts[1]}"


def _goal_formatter_result(
    repository: Path,
    source_commit: str,
    contract_path: str,
    contract_bytes: bytes,
) -> tuple[EnumOccEligibilityReason | None, str]:
    """Check the committed contract with the repository's pinned yamlfmt."""
    config_result = _git(repository, "show", f"{source_commit}:.pre-commit-config.yaml")
    fmt_result = _git(repository, "show", f"{source_commit}:.yamlfmt")
    if config_result.returncode or fmt_result.returncode:
        return (
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the source revision does not expose the repository formatter policy",
        )
    try:
        config = yaml.load(config_result.stdout, Loader=yaml.SafeLoader)
        entries = config.get("repos", []) if isinstance(config, dict) else []
        pinned = any(
            isinstance(entry, dict)
            and entry.get("repo") == "https://github.com/google/yamlfmt"
            and entry.get("rev") == "v0.21.0"
            for entry in entries
        )
    except (UnicodeDecodeError, yaml.YAMLError, AttributeError):
        return (
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the source revision formatter policy could not be read",
        )
    if not pinned:
        return (
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the source revision does not pin the supported yamlfmt version",
        )

    formatter = shutil.which("yamlfmt")
    if formatter is None:
        return (
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the pinned yamlfmt executable is unavailable",
        )
    try:
        version = subprocess.run(
            (formatter, "-version"),
            check=False,
            capture_output=True,
            timeout=5.0,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return (
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the pinned yamlfmt executable is unavailable",
        )
    if version.returncode or not version.stdout.strip().startswith("yamlfmt 0.21.0"):
        return (
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the available formatter does not match the committed yamlfmt pin",
        )

    with tempfile.TemporaryDirectory(prefix="omn20070-goal-format-") as temp_dir:
        directory = Path(temp_dir)
        config_path = directory / ".yamlfmt"
        source_path = directory / Path(contract_path).name
        config_path.write_bytes(fmt_result.stdout)
        source_path.write_bytes(contract_bytes)
        try:
            checked = subprocess.run(
                (
                    formatter,
                    "-lint",
                    "-conf",
                    str(config_path),
                    "-no_global_conf",
                    str(source_path),
                ),
                check=False,
                capture_output=True,
                timeout=10.0,
                text=True,
            )
        except subprocess.TimeoutExpired:
            return (
                EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
                "the pinned contract formatter timed out",
            )
        except OSError:
            return (
                EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
                "the pinned contract formatter could not be executed",
            )
    if checked.returncode:
        return (
            EnumOccEligibilityReason.CONTRACT_FORMAT_INVALID,
            "the committed goal contract fails the repository's pinned yamlfmt policy",
        )
    return None, ""


def _validate_goal_eligibility(
    snapshot: ModelOccEligibilityInput,
    *,
    allocation: ModelGoalAttemptAllocationSnapshot | None,
    admission_provider: ProtocolGoalAdmissionProvider,
) -> ModelOccEligibilityResult:
    """Validate explicit goal source, subject, and receipt bindings."""
    assert snapshot.goal_id is not None
    assert snapshot.contract_revision is not None
    assert snapshot.contract_schema_version is not None
    assert snapshot.goal_contract_root is not None
    assert snapshot.goal_contract_path is not None
    assert snapshot.goal_contract_source_commit_sha is not None
    assert snapshot.goal_contract_sha256 is not None
    assert snapshot.subject_commit_sha is not None
    assert snapshot.subject_tree_sha is not None

    provenance = {
        "goal_id": snapshot.goal_id,
        "repository": snapshot.repo,
        "contract_revision": snapshot.contract_revision,
        "contract_schema_version": snapshot.contract_schema_version,
        "goal_contract_path": snapshot.goal_contract_path,
        "goal_contract_source_commit_sha": snapshot.goal_contract_source_commit_sha,
        "goal_contract_sha256": snapshot.goal_contract_sha256,
        "subject_commit_sha": snapshot.subject_commit_sha,
        "subject_tree_sha": snapshot.subject_tree_sha,
    }
    mutation_state: ModelGoalMutationState | None = None
    admission_observation: ModelGoalAdmissionObservation | None = None
    dependency_admission_observation_refs: dict[str, tuple[UUID, str]] = {}

    def result(
        eligible: bool,
        reason: EnumOccEligibilityReason,
        detail: str,
        *,
        hashes: dict[str, str] | None = None,
        receipts: tuple[str, ...] = (),
        missing: tuple[str, ...] = (),
        stale: tuple[str, ...] = (),
        goal_revision_history_sha256: str | None = None,
        goal_policy_revision: UUID | None = None,
        goal_revision_history_store_revision: UUID | None = None,
        criterion_baseline_sha256: str | None = None,
        criterion_coverage_sha256: str | None = None,
        evaluation_observation: ModelGoalEvaluationObservation | None = None,
        mutation_state_override: ModelGoalMutationState | None = None,
    ) -> ModelOccEligibilityResult:
        return _goal_result(
            snapshot,
            allocation=allocation,
            eligible=eligible,
            reason=reason,
            detail=detail,
            contract_hashes=hashes,
            receipt_ids=receipts,
            missing=missing,
            stale=stale,
            goal_revision_history_sha256=goal_revision_history_sha256,
            goal_policy_revision=goal_policy_revision,
            goal_revision_history_store_revision=goal_revision_history_store_revision,
            criterion_baseline_sha256=criterion_baseline_sha256,
            criterion_coverage_sha256=criterion_coverage_sha256,
            evaluation_observation=evaluation_observation,
            admission_observation=admission_observation,
            dependency_admission_observation_refs=dependency_admission_observation_refs,
            mutation_state=mutation_state_override or mutation_state,
        )

    root = snapshot.goal_contract_root
    try:
        remote_result = _git(root, "remote", "get-url", "origin")
    except (OSError, subprocess.TimeoutExpired):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the goal contract repository remote could not be inspected",
        )
    if remote_result.returncode:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the goal contract repository has no readable origin remote",
        )
    remote_repo = _remote_repository(
        remote_result.stdout.decode("utf-8", "replace").strip()
    )
    if remote_repo is None or remote_repo.casefold() != snapshot.repo.casefold():
        return result(
            False,
            EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH,
            "the goal source repository remote does not match the declared repository",
        )

    try:
        source = _git(
            root,
            "show",
            f"{snapshot.goal_contract_source_commit_sha}:{snapshot.goal_contract_path.as_posix()}",
        )
        subject_tree = _git(
            root,
            "rev-parse",
            f"{snapshot.subject_commit_sha}^{{tree}}",
        )
    except (OSError, subprocess.TimeoutExpired):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "Git source or subject proof could not be read",
        )
    if source.returncode:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
            "the declared contract path is absent at its immutable source commit",
        )
    if (
        subject_tree.returncode
        or subject_tree.stdout.decode().strip() != snapshot.subject_tree_sha
    ):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH,
            "the declared subject tree does not match the Git tree for subject_commit_sha",
        )
    format_reason, format_detail = _goal_formatter_result(
        root,
        snapshot.goal_contract_source_commit_sha,
        snapshot.goal_contract_path.as_posix(),
        source.stdout,
    )
    if format_reason is not None:
        return result(False, format_reason, format_detail)

    try:
        source_text = source.stdout.decode("utf-8")
        # The custom loader subclasses SafeLoader and only rejects duplicate
        # mapping keys; it never constructs arbitrary Python objects.
        contract = yaml.load(
            source_text,
            Loader=_DuplicateKeySafeLoader,  # noqa: S506
        )
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
            f"the immutable goal contract is not unambiguous UTF-8 YAML: {exc.__class__.__name__}",
        )
    if not isinstance(contract, dict):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
            "the immutable goal contract root must be a mapping",
        )
    try:
        contract_goal_id = UUID(str(contract.get("goal_id", "")))
        contract_revision = UUID(str(contract.get("contract_revision", "")))
    except ValueError:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
            "the immutable goal contract must declare UUID goal_id and contract_revision",
        )
    if (
        contract.get("repository") != snapshot.repo
        or contract_goal_id != snapshot.goal_id
        or contract_revision != snapshot.contract_revision
        or contract.get("schema_version")
        != snapshot.contract_schema_version.to_string()
        or (
            snapshot.goal_ticket_id is not None
            and contract.get("ticket_id") != snapshot.goal_ticket_id
        )
    ):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
            "the immutable contract identity differs from the explicit goal snapshot",
        )
    if compute_canonical_contract_sha256(contract) != snapshot.goal_contract_sha256:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
            "the immutable goal contract canonical digest does not match the declaration",
        )
    raw_manifest = contract.get("subject_manifest")
    if not isinstance(raw_manifest, dict):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
            "the immutable goal subject manifest is absent or invalid: mapping required",
        )
    try:
        contract_manifest = ModelGoalSubjectManifest.model_validate(raw_manifest)
    except ValidationError as exc:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
            "the immutable goal subject manifest is absent or invalid: "
            f"{exc.__class__.__name__}",
        )
    if contract_manifest.required_subject_kind == "commit":
        if contract_manifest.commit_source == "pull_request":
            if (
                snapshot.pr_number is None
                or snapshot.subject_commit_sha
                not in _normalize_sha_set(snapshot.pr_commit_shas)
                or contract_manifest.subject_ref is None
                or snapshot.pr_branch
                != contract_manifest.subject_ref.removeprefix("refs/heads/")
            ):
                return result(
                    False,
                    EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH,
                    "the PR subject does not match the protected PR ref and head",
                )
        elif snapshot.pr_number is not None or snapshot.pr_commit_shas:
            return result(
                False,
                EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH,
                "the protected branch subject cannot include PR metadata",
            )
    # PR metadata on the legacy envelope is not authority for merge-group or
    # deployment subjects. Those modes resolve only from their typed protected
    # observation fields below.
    try:
        contract_manifest.validate_for_owner(
            repository=snapshot.repo, goal_id=snapshot.goal_id
        )
    except ModelOnexError as exc:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
            f"the immutable goal subject manifest has an invalid dependency cycle: {exc}",
        )
    raw_items = contract.get("dod_evidence")
    if not isinstance(raw_items, list) or not raw_items:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
            "the goal contract must declare at least one evidence item",
        )
    try:
        evidence_items = tuple(
            ModelDodEvidenceItem.model_validate(raw_item) for raw_item in raw_items
        )
    except ValidationError as exc:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
            f"the goal contract evidence is structurally invalid: {exc.__class__.__name__}",
        )

    entries: dict[
        tuple[str, str], tuple[ModelDodEvidenceItem, ModelDodEvidenceCheck]
    ] = {}
    for item in evidence_items:
        if (
            not item.id
            or item.id in {".", ".."}
            or "/" in item.id
            or "\\" in item.id
            or "\x00" in item.id
        ):
            return result(
                False,
                EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
                "goal evidence item id must be a single safe path component",
            )
        for check in item.checks:
            key = (item.id, check.check_type.value)
            if key in entries:
                return result(
                    False,
                    EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
                    "the goal contract repeats an item/check key",
                )
            entries[key] = (item, check)
    if not entries:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CONTRACT_INVALID,
            "the goal contract has no declared checks",
        )

    try:
        policy = admission_provider.get_policy(
            repository=snapshot.repo,
            goal_id=snapshot.goal_id,
            contract_revision=snapshot.contract_revision,
        )
    except GoalAdmissionProviderError:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the protected verifier policy could not be read",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
        )
    if (
        policy is None
        or policy.criterion_baseline is None
        or policy.subject_manifest is None
    ):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "no protected goal verifier policy and criterion baseline are configured",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
        )
    if (
        policy.repository != snapshot.repo
        or policy.goal_id != snapshot.goal_id
        or policy.contract_revision != snapshot.contract_revision
        or policy.subject_manifest != contract_manifest
    ):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID,
            "protected verifier policy is bound to a different goal revision",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
        )

    try:
        revision_history = admission_provider.read_current_revision_history(
            repository=snapshot.repo,
            goal_id=snapshot.goal_id,
        )
    except GoalAdmissionProviderError:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the trusted goal revision history could not be read",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
        )
    if revision_history is None:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "no complete trusted goal revision history is available",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
        )
    revision_reason, revision_detail, revision_history_digest = (
        _validate_goal_revision_history(
            snapshot, revision_history, admission_provider=admission_provider
        )
    )
    if revision_reason is not None:
        return result(
            False,
            revision_reason,
            revision_detail,
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
        )
    assert revision_history_digest is not None

    coverage_result = _validate_goal_criterion_coverage(
        root=root,
        subject_commit_sha=snapshot.subject_commit_sha,
        evidence_items=evidence_items,
        policy=policy,
    )
    coverage_reason, coverage_detail, baseline_digest, coverage_digest = coverage_result
    if coverage_reason is not None:
        return result(
            False,
            coverage_reason,
            coverage_detail,
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
        )
    assert baseline_digest is not None
    assert coverage_digest is not None

    try:
        observation = admission_provider.get_evaluation_observation(
            repository=snapshot.repo,
            goal_id=snapshot.goal_id,
            contract_revision=snapshot.contract_revision,
            subject_commit_sha=snapshot.subject_commit_sha,
            subject_tree_sha=snapshot.subject_tree_sha,
        )
    except GoalAdmissionProviderError:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the protected evaluation observation could not be read",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
        )
    if observation is None:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "no protected evaluation observation and deadline event are available",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
        )
    if (
        observation.repository != snapshot.repo
        or observation.goal_id != snapshot.goal_id
        or observation.contract_revision != snapshot.contract_revision
        or observation.subject_commit_sha != snapshot.subject_commit_sha
        or observation.subject_tree_sha != snapshot.subject_tree_sha
    ):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID,
            "the protected evaluation observation is bound to a different subject",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
            evaluation_observation=observation,
        )
    try:
        contract_manifest.validate_observation_subject(observation)
    except ModelOnexError as exc:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID,
            f"protected subject manifest does not match the evaluation observation: {exc}",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
            evaluation_observation=observation,
        )
    if contract_manifest.required_subject_kind == "commit":
        if contract_manifest.commit_source == "pull_request":
            assert snapshot.pr_number is not None
        try:
            current_source = admission_provider.read_current_commit_source(
                repository=snapshot.repo,
                goal_id=snapshot.goal_id,
                contract_revision=snapshot.contract_revision,
                manifest=contract_manifest,
                pull_request_number=snapshot.pr_number,
            )
        except (GoalAdmissionProviderError, AttributeError):
            return result(
                False,
                EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
                "the current protected commit source could not be read",
                hashes={
                    str(snapshot.goal_id): compute_canonical_contract_sha256(contract)
                },
                evaluation_observation=observation,
            )
        if current_source is None:
            return result(
                False,
                EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
                "the current protected commit source is unavailable",
                hashes={
                    str(snapshot.goal_id): compute_canonical_contract_sha256(contract)
                },
                evaluation_observation=observation,
            )
        if (
            current_source.repository != snapshot.repo
            or current_source.goal_id != snapshot.goal_id
            or current_source.contract_revision != snapshot.contract_revision
            or current_source.commit_source != contract_manifest.commit_source
            or current_source.subject_ref != contract_manifest.subject_ref
            or current_source.subject_repository != observation.subject_repository
            or current_source.subject_commit_sha != snapshot.subject_commit_sha
            or current_source.subject_commit_sha != observation.subject_commit_sha
            or current_source.subject_tree_sha != snapshot.subject_tree_sha
            or current_source.subject_tree_sha != observation.subject_tree_sha
            or current_source.pull_request_number != observation.pull_request_number
            or current_source.base_repository != observation.base_repository
            or current_source.base_ref != contract_manifest.base_ref
            or current_source.base_ref != observation.base_ref
            or current_source.observed_at < observation.observed_at
            or current_source.observed_at > observation.deadline_at
        ):
            return result(
                False,
                EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH,
                "current PR/branch source readback differs from the protected subject",
                hashes={
                    str(snapshot.goal_id): compute_canonical_contract_sha256(contract)
                },
                evaluation_observation=observation,
            )
    elif contract_manifest.required_subject_kind == "merge_group":
        try:
            current_group = admission_provider.read_current_merge_group_source(
                repository=snapshot.repo,
                goal_id=snapshot.goal_id,
                contract_revision=snapshot.contract_revision,
                observation=observation,
            )
        except (GoalAdmissionProviderError, AttributeError):
            return result(
                False,
                EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
                "the retained merge-group source could not be read",
                hashes={
                    str(snapshot.goal_id): compute_canonical_contract_sha256(contract)
                },
                evaluation_observation=observation,
            )
        if current_group is None:
            return result(
                False,
                EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
                "no current authenticated merge-group source is available",
                hashes={
                    str(snapshot.goal_id): compute_canonical_contract_sha256(contract)
                },
                evaluation_observation=observation,
            )
        if (
            current_group.repository != snapshot.repo
            or current_group.goal_id != snapshot.goal_id
            or current_group.contract_revision != snapshot.contract_revision
            or current_group.delivery_id != observation.merge_group_delivery_id
            or current_group.merge_group_id != observation.merge_group_id
            or current_group.merge_group_ref != observation.merge_group_ref
            or current_group.base_ref != observation.merge_group_base_ref
            or current_group.head_ref != observation.merge_group_head_ref
            or current_group.base_sha != observation.merge_group_base_sha
            or current_group.base_tree_sha != observation.merge_group_base_tree_sha
            or current_group.head_sha != observation.merge_group_head_sha
            or current_group.head_tree_sha != observation.merge_group_head_tree_sha
            or current_group.head_sha != snapshot.subject_commit_sha
            or current_group.head_tree_sha != snapshot.subject_tree_sha
            or current_group.source_checkpoint_id
            != observation.merge_group_source_checkpoint_id
            or current_group.source_body_sha256
            != observation.merge_group_source_body_sha256
            or current_group.received_at != observation.merge_group_received_at
            or current_group.observed_at < observation.observed_at
            or current_group.observed_at > observation.deadline_at
        ):
            return result(
                False,
                EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH,
                "current merge-group readback differs from the retained subject delivery",
                hashes={
                    str(snapshot.goal_id): compute_canonical_contract_sha256(contract)
                },
                evaluation_observation=observation,
            )

    try:
        mutation_state = admission_provider.read_current_goal_mutation_state(
            repository=snapshot.repo,
            goal_id=snapshot.goal_id,
        )
    except (GoalAdmissionProviderError, AttributeError):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the protected goal mutation barrier could not be read",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
            evaluation_observation=observation,
        )
    if (
        mutation_state is None
        or mutation_state.repository != snapshot.repo
        or mutation_state.goal_id != snapshot.goal_id
    ):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "no current protected goal mutation barrier snapshot is available",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
            evaluation_observation=observation,
        )
    if mutation_state.status != "clear":
        return result(
            False,
            EnumOccEligibilityReason.GOAL_MUTATION_PENDING,
            "an unresolved or confirmed-but-not-activated mutation blocks admission",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
            goal_revision_history_sha256=revision_history_digest,
            goal_policy_revision=policy.policy_revision,
            goal_revision_history_store_revision=revision_history.store_revision,
            criterion_baseline_sha256=baseline_digest,
            criterion_coverage_sha256=coverage_digest,
            evaluation_observation=observation,
            mutation_state_override=mutation_state,
        )
    if observation.deadline_status == "expired":
        return result(
            False,
            EnumOccEligibilityReason.GOAL_DEADLINE_EXPIRED,
            "a trusted persisted deadline occurrence blocks this goal subject",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
            goal_revision_history_sha256=revision_history_digest,
            goal_policy_revision=policy.policy_revision,
            goal_revision_history_store_revision=revision_history.store_revision,
            criterion_baseline_sha256=baseline_digest,
            criterion_coverage_sha256=coverage_digest,
            evaluation_observation=observation,
        )

    if allocation is None:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "no authoritative durable attempt allocation snapshot was supplied",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
            goal_revision_history_sha256=revision_history_digest,
            goal_policy_revision=policy.policy_revision,
            goal_revision_history_store_revision=revision_history.store_revision,
            criterion_baseline_sha256=baseline_digest,
            criterion_coverage_sha256=coverage_digest,
            evaluation_observation=observation,
        )
    if (
        allocation.goal_id != snapshot.goal_id
        or allocation.repository != snapshot.repo
        or allocation.contract_revision != snapshot.contract_revision
        or allocation.subject_commit_sha != snapshot.subject_commit_sha
        or allocation.subject_tree_sha != snapshot.subject_tree_sha
    ):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH,
            "attempt allocation partition does not match the verified goal subject",
            evaluation_observation=observation,
        )
    selected_attempt = max(allocation.attempts, key=lambda attempt: attempt.sequence)
    if selected_attempt.status is not EnumGoalAttemptStatus.PASS:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ATTEMPT_NONPASS,
            "highest allocated attempt "
            f"{selected_attempt.sequence} is {selected_attempt.status.value}; "
            "an older PASS cannot admit this subject",
            hashes={str(snapshot.goal_id): compute_canonical_contract_sha256(contract)},
            goal_revision_history_sha256=revision_history_digest,
            goal_policy_revision=policy.policy_revision,
            goal_revision_history_store_revision=revision_history.store_revision,
            criterion_baseline_sha256=baseline_digest,
            criterion_coverage_sha256=coverage_digest,
            evaluation_observation=observation,
        )

    contract_digest = compute_canonical_contract_sha256(contract)
    # In goal mode the retained signed execution result R is the check evidence.
    # Per-check YAML files remain a legacy ticket/OCC input and are never read
    # through a caller-selected filesystem path here.
    passed_receipts: list[str] = []

    try:
        attestation = admission_provider.get_attestation(
            repository=snapshot.repo,
            goal_id=snapshot.goal_id,
            contract_revision=snapshot.contract_revision,
            subject_commit_sha=snapshot.subject_commit_sha,
            subject_tree_sha=snapshot.subject_tree_sha,
            attempt_id=selected_attempt.attempt_id,
            attempt_sequence=selected_attempt.sequence,
            store_revision=allocation.store_revision,
        )
    except GoalAdmissionProviderError:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the trusted supervisor attestation could not be read",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )
    if attestation is None:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "the selected attempt has no trusted supervisor attestation",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )

    try:
        contract_manifest.validate_observation_subject(observation)
        contract_manifest.validate_parent_integration_criterion(
            protected_criterion_ids={
                requirement.criterion_id
                for requirement in policy.criterion_baseline.requirements
            }
        )
    except ModelOnexError as exc:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID,
            f"protected subject manifest does not match policy or observation: {exc}",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )

    try:
        execution_receipt = admission_provider.get_execution_receipt(
            repository=snapshot.repo,
            goal_id=snapshot.goal_id,
            contract_revision=snapshot.contract_revision,
            subject_commit_sha=snapshot.subject_commit_sha,
            subject_tree_sha=snapshot.subject_tree_sha,
            attempt_id=selected_attempt.attempt_id,
            attempt_sequence=selected_attempt.sequence,
        )
    except GoalAdmissionProviderError:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the trusted isolated-execution receipt could not be read",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )
    if execution_receipt is None:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "the selected PASS attempt has no isolated-execution receipt",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )

    assert selected_attempt.result_sha256 is not None
    try:
        result_bytes = admission_provider.read_artifact_bytes(
            selected_attempt.result_sha256
        )
    except GoalAdmissionProviderError:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "the immutable execution result R could not be validated",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )
    if result_bytes is None:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "the immutable execution result R could not be validated",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )
    try:
        execution_result = ModelGoalExecutionResult.model_validate_json(result_bytes)
    except (ValidationError, ValueError):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "the immutable execution result R could not be validated",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )

    try:
        admission_observation = admission_provider.read_current_admission_observation(
            attempts=allocation,
            policy=policy,
            observation=observation,
            execution_receipt=execution_receipt,
            attestation=attestation,
        )
    except GoalAdmissionProviderError:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the protected final-admission observation could not be read",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )
    if admission_observation is None:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "the selected attempt has no current protected final-admission observation",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )

    expected_request_sha256 = compute_goal_execution_request_sha256(
        repository=snapshot.repo,
        goal_id=snapshot.goal_id,
        contract_revision=snapshot.contract_revision,
        contract_sha256=contract_digest,
        policy_revision=policy.policy_revision,
        verifier_artifact_sha256=policy.verifier_artifact_sha256,
        criterion_baseline_sha256=baseline_digest,
        revision_history_sha256=revision_history_digest,
        evaluation_observation_sha256=observation.content_sha256(),
        subject_manifest_sha256=contract_manifest.content_sha256(),
        attempt_id=selected_attempt.attempt_id,
        attempt_sequence=selected_attempt.sequence,
        subject_kind=contract_manifest.required_subject_kind,
        subject_commit_sha=snapshot.subject_commit_sha,
        subject_tree_sha=snapshot.subject_tree_sha,
    )
    attempt_snapshot = allocation.snapshot_sha256
    if (
        execution_result.attempt_id != selected_attempt.attempt_id
        or execution_result.content_sha256() != selected_attempt.result_sha256
        or execution_result.artifact_sha256
        != tuple(sorted(selected_attempt.artifact_sha256))
        or selected_attempt.running_store_revision is None
        or selected_attempt.running_snapshot_sha256 is None
        or execution_receipt.execution_record_id != attestation.execution_record_id
        or execution_receipt.issuer_domain != policy.issuer_domain
        or execution_receipt.repository != snapshot.repo
        or execution_receipt.goal_id != snapshot.goal_id
        or execution_receipt.contract_revision != snapshot.contract_revision
        or execution_receipt.contract_schema_version.to_string()
        != snapshot.contract_schema_version.to_string()
        or execution_receipt.contract_path != snapshot.goal_contract_path
        or execution_receipt.contract_source_commit_sha
        != snapshot.goal_contract_source_commit_sha
        or execution_receipt.contract_sha256 != contract_digest
        or execution_receipt.subject_commit_sha != snapshot.subject_commit_sha
        or execution_receipt.subject_tree_sha != snapshot.subject_tree_sha
        or execution_receipt.attempt_id != selected_attempt.attempt_id
        or execution_receipt.attempt_sequence != selected_attempt.sequence
        or execution_receipt.running_attempt_store_revision
        != selected_attempt.running_store_revision
        or execution_receipt.running_attempt_snapshot_sha256
        != selected_attempt.running_snapshot_sha256
        or execution_receipt.execution_request_sha256 != expected_request_sha256
        or selected_attempt.execution_request_sha256 != expected_request_sha256
        or execution_receipt.result_sha256 != execution_result.content_sha256()
        or execution_receipt.artifact_sha256 != execution_result.artifact_sha256
        or execution_receipt.subject_manifest_sha256
        != contract_manifest.content_sha256()
        or execution_receipt.evaluation_observation_sha256
        != observation.content_sha256()
        or execution_receipt.verifier_artifact_sha256 != policy.verifier_artifact_sha256
        or execution_receipt.policy_revision != policy.policy_revision
        or execution_receipt.execution_identity
        not in policy.allowed_execution_identities
        or execution_receipt.completed_at > observation.deadline_at
        or attestation.issued_at < execution_receipt.completed_at
        or selected_attempt.result_sha256 != execution_receipt.result_sha256
        or selected_attempt.running_store_revision == allocation.store_revision
        or attempt_snapshot == execution_receipt.running_attempt_snapshot_sha256
    ):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID,
            "isolated execution receipt, R, or allocation snapshot has inconsistent bindings",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )

    try:
        contract_manifest.validate_parent_integration_result(execution_result)
    except ModelOnexError as exc:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CRITERION_COVERAGE_MISSING,
            str(exc),
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )

    protected_checks = {
        (
            requirement.criterion_id,
            check.item_id,
            check.check_type,
            check.check_value_sha256,
        )
        for requirement in policy.criterion_baseline.requirements
        for check in requirement.required_checks
    }
    result_checks = {
        (
            outcome.criterion_id,
            outcome.item_id,
            outcome.check_type,
            outcome.check_value_sha256,
        ): outcome.outcome
        for outcome in execution_result.raw_check_outcomes
    }
    criterion_outcomes = {
        item.criterion_id: item.outcome for item in execution_result.criterion_evidence
    }
    protected_selectors = {
        selector
        for requirement in policy.criterion_baseline.requirements
        for selector in requirement.required_test_selectors
    }
    observed_selectors = {
        item.selector: item.outcome for item in execution_result.selector_outcomes
    }
    coverage_mismatch = []
    if set(result_checks) != protected_checks:
        coverage_mismatch.append("check bindings")
    if any(outcome != "passed" for outcome in result_checks.values()):
        coverage_mismatch.append("check outcomes")
    expected_criteria = {
        requirement.criterion_id
        for requirement in policy.criterion_baseline.requirements
    }
    if set(criterion_outcomes) != expected_criteria:
        coverage_mismatch.append("criterion bindings")
    if any(outcome != "passed" for outcome in criterion_outcomes.values()):
        coverage_mismatch.append("criterion outcomes")
    if set(observed_selectors) != protected_selectors:
        coverage_mismatch.append("selector bindings")
    if any(outcome != "passed" for outcome in observed_selectors.values()):
        coverage_mismatch.append("selector outcomes")
    if coverage_mismatch:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_CRITERION_COVERAGE_MISSING,
            "execution result R does not pass the exact protected criterion/check/selector baseline",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )

    expected_artifacts = tuple(sorted(selected_attempt.artifact_sha256))
    if (
        attestation.issuer_domain != policy.issuer_domain
        or attestation.goal_id != snapshot.goal_id
        or attestation.repository != snapshot.repo
        or attestation.contract_revision != snapshot.contract_revision
        or attestation.contract_schema_version.to_string()
        != snapshot.contract_schema_version.to_string()
        or attestation.contract_path != snapshot.goal_contract_path
        or attestation.contract_source_commit_sha
        != snapshot.goal_contract_source_commit_sha
        or attestation.contract_sha256 != contract_digest
        or attestation.subject_commit_sha != snapshot.subject_commit_sha
        or attestation.subject_tree_sha != snapshot.subject_tree_sha
        or attestation.attempt_id != selected_attempt.attempt_id
        or attestation.attempt_sequence != selected_attempt.sequence
        or attestation.attempt_result_sha256 != selected_attempt.result_sha256
        or attestation.execution_record_id != execution_receipt.execution_record_id
        or attestation.execution_receipt_sha256 != execution_receipt.content_sha256()
        or tuple(sorted(attestation.attempt_artifact_sha256)) != expected_artifacts
        or attestation.attempt_store_revision != allocation.store_revision
        or attestation.attempt_snapshot_sha256 != allocation.snapshot_sha256
        or attestation.verifier_artifact_sha256 != policy.verifier_artifact_sha256
        or attestation.policy_revision != policy.policy_revision
        or attestation.criterion_baseline_sha256 != baseline_digest
        or attestation.criterion_coverage_sha256 != coverage_digest
        or attestation.revision_history_sha256 != revision_history_digest
        or attestation.evaluation_observation_id != observation.observation_id
        or attestation.deadline_event_id != observation.deadline_event_id
        or attestation.subject_manifest_sha256 != contract_manifest.content_sha256()
        or attestation.evaluation_observation_sha256 != observation.content_sha256()
        or attestation.execution_identity not in policy.allowed_execution_identities
        or not _admission_observation_matches(
            admission_observation=admission_observation,
            attempts=allocation,
            policy=policy,
            observation=observation,
            execution_receipt=execution_receipt,
            attestation=attestation,
            contract_sha256=contract_digest,
            criterion_baseline_sha256=baseline_digest,
            criterion_coverage_sha256=coverage_digest,
            revision_history_sha256=revision_history_digest,
        )
    ):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID,
            "supervisor evidence does not match the active protected policy or goal subject",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )

    try:
        trust_root = admission_provider.get_domain_trust_root(policy.issuer_domain)
    except GoalAdmissionProviderError:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the supervisor trust root could not be read",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )
    if trust_root is None:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "the supervisor issuer has no active trusted key",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )
    dependency_artifacts: set[str] = set()
    dependency_issuer_by_id = {
        binding.dependency_id: binding.issuer_domain
        for binding in policy.dependency_issuer_bindings
    }
    if set(dependency_issuer_by_id) != {
        pin.dependency_id for pin in contract_manifest.dependencies
    }:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "protected policy must bind exactly one trusted issuer domain per dependency",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )
    for pin in contract_manifest.dependencies:
        try:
            dependency_evidence = admission_provider.get_dependency_evidence(
                dependency=pin
            )
        except GoalAdmissionProviderError:
            return result(
                False,
                EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
                f"protected dependency evidence {pin.dependency_id!r} could not be read",
                hashes={str(snapshot.goal_id): contract_digest},
                receipts=tuple(sorted(passed_receipts)),
            )
        if dependency_evidence is None:
            return result(
                False,
                EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
                f"protected dependency evidence {pin.dependency_id!r} is unavailable",
                hashes={str(snapshot.goal_id): contract_digest},
                receipts=tuple(sorted(passed_receipts)),
            )
        dependency_attempts = dependency_evidence.attempts
        dependency_policy = dependency_evidence.policy
        dependency_observation = dependency_evidence.initial_observation
        dependency_execution = dependency_evidence.execution_receipt
        dependency_attestation = dependency_evidence.attestation
        dependency_admission_observation = dependency_evidence.admission_observation
        dependency_admission_observation_refs[pin.dependency_id] = (
            dependency_admission_observation.observation_id,
            dependency_admission_observation.content_sha256(),
        )
        expected_dependency_issuer = dependency_issuer_by_id[pin.dependency_id]
        try:
            dependency_key = admission_provider.get_domain_trust_root(
                expected_dependency_issuer
            )
        except GoalAdmissionProviderError:
            return result(
                False,
                EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
                f"dependency trust root {dependency_attestation.issuer_domain!r} could not be read",
                hashes={str(snapshot.goal_id): contract_digest},
                receipts=tuple(sorted(passed_receipts)),
            )
        dependency_baseline = dependency_policy.criterion_baseline
        dependency_selected_attempt = max(
            dependency_attempts.attempts, key=lambda attempt: attempt.sequence
        )
        if (
            dependency_key is None
            or dependency_attestation.issuer_domain != expected_dependency_issuer
            or dependency_policy.issuer_domain != expected_dependency_issuer
            or dependency_policy.repository != pin.repository
            or dependency_policy.goal_id != pin.goal_id
            or dependency_policy.contract_revision != pin.contract_revision
            or dependency_baseline is None
            or dependency_baseline.content_sha256()
            != dependency_attestation.criterion_baseline_sha256
            or dependency_policy.subject_manifest is None
            or dependency_policy.subject_manifest.content_sha256()
            != dependency_attestation.subject_manifest_sha256
            or dependency_policy.policy_revision
            != dependency_attestation.policy_revision
            or dependency_policy.verifier_artifact_sha256
            != dependency_attestation.verifier_artifact_sha256
            or dependency_policy.max_attestation_age_seconds < 1
            or dependency_attempts.repository != pin.repository
            or dependency_attempts.goal_id != pin.goal_id
            or dependency_attempts.contract_revision != pin.contract_revision
            or dependency_attempts.subject_commit_sha != pin.subject_commit_sha
            or dependency_attempts.subject_tree_sha != pin.subject_tree_sha
            or dependency_selected_attempt.status is not EnumGoalAttemptStatus.PASS
            or dependency_attestation.attempt_id
            != dependency_selected_attempt.attempt_id
            or dependency_attestation.attempt_sequence
            != dependency_selected_attempt.sequence
            or dependency_attestation.attempt_store_revision
            != dependency_attempts.store_revision
            or dependency_attestation.attempt_snapshot_sha256
            != dependency_attempts.snapshot_sha256
            or not pin.matches_signed_evidence(
                attestation=dependency_attestation,
                observation=dependency_observation,
            )
            or not dependency_attestation.binds_evaluation_observation(
                dependency_observation
            )
            or dependency_observation.deadline_status != "open"
            or dependency_observation.deadline_recorded_at is not None
            or dependency_execution.issuer_domain != expected_dependency_issuer
            or dependency_execution.repository != pin.repository
            or dependency_execution.goal_id != pin.goal_id
            or dependency_execution.contract_revision != pin.contract_revision
            or dependency_execution.contract_schema_version.to_string()
            != dependency_attestation.contract_schema_version.to_string()
            or dependency_execution.contract_path
            != dependency_attestation.contract_path
            or dependency_execution.contract_source_commit_sha
            != dependency_attestation.contract_source_commit_sha
            or dependency_execution.contract_sha256 != pin.contract_sha256
            or dependency_execution.subject_commit_sha != pin.subject_commit_sha
            or dependency_execution.subject_tree_sha != pin.subject_tree_sha
            or dependency_execution.attempt_id != dependency_selected_attempt.attempt_id
            or dependency_execution.attempt_sequence
            != dependency_selected_attempt.sequence
            or dependency_execution.running_attempt_store_revision
            != dependency_selected_attempt.running_store_revision
            or dependency_execution.running_attempt_snapshot_sha256
            != dependency_selected_attempt.running_snapshot_sha256
            or dependency_execution.execution_request_sha256
            != dependency_selected_attempt.execution_request_sha256
            or dependency_execution.result_sha256
            != dependency_selected_attempt.result_sha256
            or dependency_execution.artifact_sha256
            != dependency_selected_attempt.artifact_sha256
            or dependency_execution.execution_record_id
            != dependency_attestation.execution_record_id
            or dependency_execution.content_sha256()
            != dependency_attestation.execution_receipt_sha256
            or dependency_execution.subject_manifest_sha256
            != dependency_attestation.subject_manifest_sha256
            or dependency_execution.policy_revision != dependency_policy.policy_revision
            or dependency_execution.execution_identity
            not in dependency_policy.allowed_execution_identities
            or not _admission_observation_matches(
                admission_observation=dependency_admission_observation,
                attempts=dependency_attempts,
                policy=dependency_policy,
                observation=dependency_observation,
                execution_receipt=dependency_execution,
                attestation=dependency_attestation,
                contract_sha256=pin.contract_sha256,
                criterion_baseline_sha256=dependency_attestation.criterion_baseline_sha256,
                criterion_coverage_sha256=dependency_attestation.criterion_coverage_sha256,
                revision_history_sha256=dependency_attestation.revision_history_sha256,
            )
            or not verify_base64(
                dependency_key,
                dependency_execution.signing_payload(),
                dependency_execution.signature,
            )
            or not verify_base64(
                dependency_key,
                dependency_attestation.signing_payload(),
                dependency_attestation.signature,
            )
        ):
            return result(
                False,
                EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID,
                f"dependency evidence {pin.dependency_id!r} does not match its trusted pin",
                hashes={str(snapshot.goal_id): contract_digest},
                receipts=tuple(sorted(passed_receipts)),
            )
        dependency_artifacts.update(pin.artifact_sha256)
    if not verify_base64(
        trust_root,
        execution_receipt.signing_payload(),
        execution_receipt.signature,
    ):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID,
            "the isolated-execution receipt signature is invalid",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )
    if not verify_base64(
        trust_root,
        attestation.signing_payload(),
        attestation.signature,
    ):
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID,
            "the supervisor attestation signature is invalid",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )

    try:
        contract_manifest.validate_produced_evidence(
            result=execution_result,
            receipt=execution_receipt,
            attestation=attestation,
            observation=observation,
        )
        contract_manifest.validate_no_self_reference(
            repository=snapshot.repo,
            goal_id=snapshot.goal_id,
            final_attestation=attestation,
        )
    except ModelOnexError as exc:
        return result(
            False,
            EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID,
            f"contract manifest evidence binding failed: {exc}",
            hashes={str(snapshot.goal_id): contract_digest},
            receipts=tuple(sorted(passed_receipts)),
        )

    artifact_digests = {
        policy.verifier_artifact_sha256,
        selected_attempt.result_sha256,
        *selected_attempt.artifact_sha256,
        *execution_result.artifact_sha256,
        *dependency_artifacts,
    }
    for digest in sorted(artifact_digests):
        try:
            artifact_bytes = admission_provider.read_artifact_bytes(digest)
        except GoalAdmissionProviderError:
            return result(
                False,
                EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
                "a pinned verifier or execution artifact could not be read",
                hashes={str(snapshot.goal_id): contract_digest},
                receipts=tuple(sorted(passed_receipts)),
            )
        if artifact_bytes is None:
            return result(
                False,
                EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
                "a pinned verifier or execution artifact is unavailable",
                hashes={str(snapshot.goal_id): contract_digest},
                receipts=tuple(sorted(passed_receipts)),
            )
        actual_digest = f"sha256:{hashlib.sha256(artifact_bytes).hexdigest()}"
        if actual_digest != digest:
            return result(
                False,
                EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID,
                "retained verifier or execution artifact bytes do not match their digest",
                hashes={str(snapshot.goal_id): contract_digest},
                receipts=tuple(sorted(passed_receipts)),
            )

    return result(
        True,
        EnumOccEligibilityReason.ELIGIBLE,
        "the current goal source, subject, protected checks, allocated attempt, "
        "signed execution receipt, and supervisor attestation verify; the caller "
        "must still publish this verdict through its serialized required-context effect",
        hashes={str(snapshot.goal_id): contract_digest},
        receipts=tuple(sorted(passed_receipts)),
        goal_revision_history_sha256=revision_history_digest,
        goal_policy_revision=policy.policy_revision,
        goal_revision_history_store_revision=revision_history.store_revision,
        criterion_baseline_sha256=baseline_digest,
        criterion_coverage_sha256=coverage_digest,
        evaluation_observation=observation,
    )


def _validate_goal_criterion_coverage(
    *,
    root: Path,
    subject_commit_sha: str,
    evidence_items: tuple[ModelDodEvidenceItem, ...],
    policy: ModelGoalVerifierPolicy,
) -> tuple[
    EnumOccEligibilityReason | None,
    str,
    str | None,
    str | None,
]:
    """Match author-declared AC bindings to protected checks and test bytes."""
    baseline = policy.criterion_baseline
    if baseline is None:
        return (
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "protected criterion baseline is unavailable",
            None,
            None,
        )

    expected: dict[str, set[tuple[str, str, str]]] = {
        requirement.criterion_id: {
            (
                check.item_id,
                check.check_type.value,
                check.check_value_sha256,
            )
            for check in requirement.required_checks
        }
        for requirement in baseline.requirements
    }
    actual: dict[str, set[tuple[str, str, str]]] = {
        criterion_id: set() for criterion_id in expected
    }
    for item in evidence_items:
        if len(set(item.binds_ac)) != len(item.binds_ac):
            return (
                EnumOccEligibilityReason.GOAL_CRITERION_BASELINE_MISMATCH,
                "an evidence item repeats an acceptance-criterion binding",
                None,
                None,
            )
        for criterion_id in item.binds_ac:
            if criterion_id not in expected:
                return (
                    EnumOccEligibilityReason.GOAL_CRITERION_BASELINE_MISMATCH,
                    "goal contract binds a criterion outside the protected baseline",
                    None,
                    None,
                )
            for check in item.checks:
                value_digest = compute_goal_check_value_sha256(check.check_value)
                actual[criterion_id].add(
                    (item.id, check.check_type.value, value_digest)
                )

    missing_criteria = tuple(
        criterion_id for criterion_id, bindings in actual.items() if not bindings
    )
    if missing_criteria:
        return (
            EnumOccEligibilityReason.GOAL_CRITERION_COVERAGE_MISSING,
            "required acceptance criteria have no check bindings: "
            + ", ".join(sorted(missing_criteria)),
            None,
            None,
        )
    missing_bindings = {
        criterion_id: expected[criterion_id] - actual[criterion_id]
        for criterion_id in expected
        if expected[criterion_id] - actual[criterion_id]
    }
    extra_bindings = {
        criterion_id: actual[criterion_id] - expected[criterion_id]
        for criterion_id in expected
        if actual[criterion_id] - expected[criterion_id]
    }
    if missing_bindings and not extra_bindings:
        return (
            EnumOccEligibilityReason.GOAL_CRITERION_COVERAGE_MISSING,
            "goal contract omits protected required checks for criteria: "
            + ", ".join(sorted(missing_bindings)),
            None,
            None,
        )
    if missing_bindings or extra_bindings:
        return (
            EnumOccEligibilityReason.GOAL_CRITERION_BASELINE_MISMATCH,
            "goal contract check bindings do not exactly match the protected criterion baseline",
            None,
            None,
        )

    protected_files: set[tuple[str, str]] = set()
    for requirement in baseline.requirements:
        for baseline_file in requirement.test_and_fixture_files:
            try:
                content = _git(
                    root,
                    "show",
                    f"{subject_commit_sha}:{baseline_file.path.as_posix()}",
                )
            except (OSError, subprocess.TimeoutExpired):
                return (
                    EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
                    "a protected criterion test/fixture could not be read from the subject commit",
                    None,
                    None,
                )
            if content.returncode:
                return (
                    EnumOccEligibilityReason.GOAL_CRITERION_BASELINE_MISMATCH,
                    "a protected criterion test/fixture is absent from the subject commit",
                    None,
                    None,
                )
            actual_digest = f"sha256:{hashlib.sha256(content.stdout).hexdigest()}"
            if actual_digest != baseline_file.sha256:
                return (
                    EnumOccEligibilityReason.GOAL_CRITERION_BASELINE_MISMATCH,
                    "a protected criterion test/fixture differs from the protected baseline",
                    None,
                    None,
                )
            protected_files.add((baseline_file.path.as_posix(), actual_digest))

    baseline_digest = baseline.content_sha256()
    coverage_digest = compute_goal_criterion_coverage_sha256(
        evidence_items=evidence_items,
        baseline=baseline,
        protected_file_sha256=dict(protected_files),
    )
    return None, "", baseline_digest, coverage_digest


def _validate_goal_revision_history(
    snapshot: ModelOccEligibilityInput,
    history: ModelGoalRevisionHistorySnapshot,
    *,
    admission_provider: ProtocolGoalAdmissionProvider,
) -> tuple[
    EnumOccEligibilityReason | None,
    str,
    str | None,
]:
    """Validate the append-only revision DAG and explicit resolution of forks."""
    assert snapshot.goal_id is not None
    assert snapshot.contract_revision is not None
    assert snapshot.contract_schema_version is not None
    assert snapshot.goal_contract_path is not None
    assert snapshot.goal_contract_source_commit_sha is not None
    assert snapshot.goal_contract_sha256 is not None

    if history.repository != snapshot.repo or history.goal_id != snapshot.goal_id:
        return (
            EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
            "revision history belongs to another repository or goal",
            None,
        )
    if history.content_sha256() != history.snapshot_sha256:
        return (
            EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
            "revision history digest does not match its complete contents",
            None,
        )
    revisions_by_id = {record.revision_id: record for record in history.revisions}
    if len(revisions_by_id) != len(history.revisions):
        return (
            EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
            "revision history repeats a revision id",
            None,
        )
    revision_policies_by_id = {
        policy.policy_revision: policy
        for policy in history.revision_authorization_policies
    }
    if len(revision_policies_by_id) != len(history.revision_authorization_policies):
        return (
            EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
            "revision history repeats an authorization policy revision",
            None,
        )
    for revision_policy in history.revision_authorization_policies:
        if (
            revision_policy.repository != snapshot.repo
            or revision_policy.goal_id != snapshot.goal_id
            or revision_policy.content_sha256() != revision_policy.policy_sha256
        ):
            return (
                EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
                "revision authorization policy is invalid or belongs to another goal",
                None,
            )
    try:
        work_ledger_key_provider = admission_provider.get_work_ledger_key_provider()
    except GoalAdmissionProviderError:
        return (
            EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
            "the Work Ledger event trust keys could not be read",
            None,
        )
    if work_ledger_key_provider is None:
        return (
            EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
            "no protected Work Ledger event signing keys are configured",
            None,
        )

    for revision in history.revisions:
        source_event = revision.source_event
        event_policy_revision = source_event.authorization_policy_revision
        authorization_policy = (
            revision_policies_by_id.get(event_policy_revision)
            if event_policy_revision is not None
            else None
        )
        if (
            authorization_policy is None
            or authorization_policy.repository != revision.repository
            or authorization_policy.goal_id != revision.goal_id
            or source_event.actor.actor_key
            not in authorization_policy.allowed_actor_keys
            or revision.source_envelope.runtime_id
            not in authorization_policy.allowed_event_runtime_ids
        ):
            return (
                EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
                "goal opening/revision issuer is not authorized by its named historical policy",
                None,
            )
        try:
            envelope_is_authentic = revision.source_envelope.verify_signature(
                work_ledger_key_provider
            )
        except ModelOnexError:
            envelope_is_authentic = False
        if not envelope_is_authentic:
            return (
                EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
                "goal opening/revision lacks an authentic signed Work Ledger envelope",
                None,
            )

    for resolution in history.fork_resolutions:
        authorization_policy = revision_policies_by_id.get(
            resolution.resolution_policy_revision
        )
        if (
            authorization_policy is None
            or resolution.repository != snapshot.repo
            or resolution.authorization_event.actor.actor_key
            not in authorization_policy.allowed_actor_keys
        ):
            return (
                EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
                "fork resolution lacks an authorized Work Ledger actor under its named policy revision",
                None,
            )
        signer = resolution.authorization_envelope.runtime_id
        if signer not in authorization_policy.allowed_event_runtime_ids:
            return (
                EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
                "fork resolution envelope signer is not authorized by its named policy revision",
                None,
            )
        try:
            envelope_is_authentic = resolution.authorization_envelope.verify_signature(
                work_ledger_key_provider
            )
        except ModelOnexError:
            envelope_is_authentic = False
        if not envelope_is_authentic:
            return (
                EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
                "fork resolution does not have an authentic signed Work Ledger envelope",
                None,
            )
    opening = revisions_by_id.get(snapshot.goal_id)
    if opening is None or opening.replaces_revision_id is not None:
        return (
            EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
            "revision history must contain the opening claim as its root revision",
            None,
        )
    children: dict[UUID, list[UUID]] = {}
    for revision in history.revisions:
        if revision.goal_id != snapshot.goal_id or revision.repository != snapshot.repo:
            return (
                EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
                "revision history contains a cross-goal or cross-repository edge",
                None,
            )
        if revision.revision_id == snapshot.goal_id:
            continue
        parent_id = revision.replaces_revision_id
        if parent_id is None or parent_id not in revisions_by_id:
            return (
                EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
                "revision edge points to a missing predecessor",
                None,
            )
        children.setdefault(parent_id, []).append(revision.revision_id)
        visited: set[UUID] = set()
        current_id = revision.revision_id
        while current_id != snapshot.goal_id:
            if current_id in visited:
                return (
                    EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
                    "revision history contains a cycle",
                    None,
                )
            visited.add(current_id)
            current = revisions_by_id.get(current_id)
            if current is None or current.replaces_revision_id is None:
                return (
                    EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
                    "revision chain does not reach its opening claim",
                    None,
                )
            current_id = current.replaces_revision_id

    resolutions_by_parent: dict[UUID, list[ModelGoalForkResolutionRecord]] = {}
    for resolution in history.fork_resolutions:
        if resolution.goal_id != snapshot.goal_id:
            return (
                EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
                "fork resolution belongs to another goal",
                None,
            )
        resolutions_by_parent.setdefault(resolution.fork_parent_revision_id, []).append(
            resolution
        )
    for parent_id, child_ids in children.items():
        resolutions = resolutions_by_parent.get(parent_id, [])
        if len(child_ids) > 1 and not resolutions:
            return (
                EnumOccEligibilityReason.GOAL_REVISION_FORK_UNRESOLVED,
                "revision fork has competing heads without an authorized resolution",
                None,
            )
        if len(child_ids) > 1:
            if len(resolutions) != 1 or set(
                resolutions[0].competing_revision_ids
            ) != set(child_ids):
                return (
                    EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
                    "fork resolution does not name every competing revision exactly once",
                    None,
                )
        elif resolutions:
            return (
                EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
                "fork resolution names a revision point with no competing heads",
                None,
            )
    if any(parent_id not in children for parent_id in resolutions_by_parent):
        return (
            EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
            "fork resolution refers to an unknown revision point",
            None,
        )

    current_revision_id = snapshot.goal_id
    while children.get(current_revision_id):
        child_ids = children[current_revision_id]
        if len(child_ids) == 1:
            current_revision_id = child_ids[0]
            continue
        resolution = resolutions_by_parent[current_revision_id][0]
        current_revision_id = resolution.selected_revision_id
    if current_revision_id != snapshot.contract_revision:
        return (
            EnumOccEligibilityReason.GOAL_REVISION_NOT_CURRENT,
            "requested contract revision is not the authorized current revision head",
            None,
        )
    current = revisions_by_id[current_revision_id]
    if (
        current.contract_schema_version != snapshot.contract_schema_version
        or current.contract_path != snapshot.goal_contract_path
        or current.contract_source_commit_sha
        != snapshot.goal_contract_source_commit_sha
        or current.contract_sha256 != snapshot.goal_contract_sha256
    ):
        return (
            EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID,
            "current revision source pin differs from the requested goal contract",
            None,
        )
    return None, "", history.snapshot_sha256


def compute_goal_criterion_coverage_sha256(
    *,
    evidence_items: tuple[ModelDodEvidenceItem | ModelContractDodItem, ...],
    baseline: ModelGoalCriterionBaseline,
    protected_file_sha256: dict[str, str] | None = None,
) -> str:
    """Return the canonical digest signed for verified criterion coverage.

    The validator calls this only after checking the candidate bindings against
    the protected baseline and reading each pinned file from the immutable
    subject commit. ``protected_file_sha256`` is therefore a verification
    result, not caller-provided authority.
    """
    requirement_ids = {item.criterion_id for item in baseline.requirements}
    bindings: dict[str, set[tuple[str, str, str]]] = {
        criterion_id: set() for criterion_id in requirement_ids
    }
    for item in evidence_items:
        for criterion_id in item.binds_ac:
            if criterion_id not in bindings:
                continue
            for check in item.checks:
                check_value_sha256 = compute_goal_check_value_sha256(check.check_value)
                bindings[criterion_id].add(
                    (item.id, check.check_type.value, check_value_sha256)
                )
    if protected_file_sha256 is None:
        protected_files = {
            (
                baseline_file.path.as_posix(),
                baseline_file.sha256,
            )
            for requirement in baseline.requirements
            for baseline_file in requirement.test_and_fixture_files
        }
    else:
        protected_files = set(protected_file_sha256.items())
    payload = {
        "criterion_bindings": {
            criterion_id: [list(binding) for binding in sorted(criterion_bindings)]
            for criterion_id, criterion_bindings in sorted(bindings.items())
        },
        "protected_files": sorted(protected_files),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def compute_goal_check_value_sha256(check_value: str | dict[str, str]) -> str:
    """Digest one typed check value using canonical compact JSON bytes."""
    canonical = json.dumps(
        check_value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def _admission_observation_matches(
    *,
    admission_observation: ModelGoalAdmissionObservation,
    attempts: ModelGoalAttemptAllocationSnapshot,
    policy: ModelGoalVerifierPolicy,
    observation: ModelGoalEvaluationObservation,
    execution_receipt: ModelGoalSupervisorExecutionReceipt,
    attestation: ModelGoalSupervisorAttestation,
    contract_sha256: str,
    criterion_baseline_sha256: str,
    criterion_coverage_sha256: str,
    revision_history_sha256: str,
) -> bool:
    """Check the trusted final observation against the exact signed proof."""
    selected_attempt = max(attempts.attempts, key=lambda attempt: attempt.sequence)
    return (
        admission_observation.repository == attempts.repository
        and admission_observation.goal_id == attempts.goal_id
        and admission_observation.contract_revision == attempts.contract_revision
        and admission_observation.subject_commit_sha == attempts.subject_commit_sha
        and admission_observation.subject_tree_sha == attempts.subject_tree_sha
        and admission_observation.attempt_id == selected_attempt.attempt_id
        and admission_observation.attempt_sequence == selected_attempt.sequence
        and admission_observation.attempt_store_revision == attempts.store_revision
        and admission_observation.attempt_snapshot_sha256 == attempts.snapshot_sha256
        and admission_observation.contract_sha256 == contract_sha256
        and admission_observation.execution_record_id
        == execution_receipt.execution_record_id
        and admission_observation.execution_receipt_sha256
        == execution_receipt.content_sha256()
        and admission_observation.attestation_id == attestation.attestation_id
        and admission_observation.attestation_sha256 == attestation.content_sha256()
        and admission_observation.policy_revision == policy.policy_revision
        and admission_observation.policy_sha256 == policy.content_sha256()
        and admission_observation.verifier_artifact_sha256
        == policy.verifier_artifact_sha256
        and admission_observation.criterion_baseline_sha256 == criterion_baseline_sha256
        and admission_observation.criterion_coverage_sha256 == criterion_coverage_sha256
        and admission_observation.revision_history_sha256 == revision_history_sha256
        and admission_observation.evaluation_observation_id
        == observation.observation_id
        and admission_observation.evaluation_observation_sha256
        == observation.content_sha256()
        and admission_observation.deadline_event_id == observation.deadline_event_id
        and admission_observation.deadline_at == observation.deadline_at
        and observation.observed_at <= execution_receipt.started_at
        and execution_receipt.completed_at <= attestation.issued_at
        and attestation.issued_at <= admission_observation.observed_at
        and admission_observation.observed_at <= observation.deadline_at
        and attestation.is_fresh_at(
            admission_observation.observed_at,
            max_age_seconds=policy.max_attestation_age_seconds,
        )
    )


def validate_occ_merge_eligibility(
    snapshot: ModelOccEligibilityInput,
    *,
    goal_admission_provider: ProtocolGoalAdmissionProvider | None = None,
) -> ModelOccEligibilityResult:
    """Validate PR merge eligibility against a pinned OCC evidence snapshot."""

    if snapshot.goal_id is not None:
        if goal_admission_provider is None:
            return _goal_result(
                snapshot,
                allocation=None,
                eligible=False,
                reason=EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
                detail=(
                    "goal admission requires a trusted attempt, policy, "
                    "attestation, and artifact provider"
                ),
            )
        assert snapshot.contract_revision is not None
        assert snapshot.subject_commit_sha is not None
        assert snapshot.subject_tree_sha is not None
        try:
            allocation = goal_admission_provider.read_current_attempt_snapshot(
                repository=snapshot.repo,
                goal_id=snapshot.goal_id,
                contract_revision=snapshot.contract_revision,
                subject_commit_sha=snapshot.subject_commit_sha,
                subject_tree_sha=snapshot.subject_tree_sha,
            )
        except GoalAdmissionProviderError:
            return _goal_result(
                snapshot,
                allocation=None,
                eligible=False,
                reason=EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE,
                detail="the authoritative attempt store could not be read",
            )
        if allocation is None:
            return _goal_result(
                snapshot,
                allocation=None,
                eligible=False,
                reason=EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE,
                detail="no durable attempt allocation exists for this exact subject",
            )
        if (
            allocation.goal_id != snapshot.goal_id
            or allocation.repository != snapshot.repo
            or allocation.contract_revision != snapshot.contract_revision
            or allocation.subject_commit_sha != snapshot.subject_commit_sha
            or allocation.subject_tree_sha != snapshot.subject_tree_sha
        ):
            return _goal_result(
                snapshot,
                allocation=allocation,
                eligible=False,
                reason=EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH,
                detail="the authoritative attempt store returned another subject partition",
            )
        return _validate_goal_eligibility(
            snapshot,
            allocation=allocation,
            admission_provider=goal_admission_provider,
        )

    # The input model enforces this for legacy OCC mode. Keep the narrowed
    # contract explicit now that goal mode permits a missing PR number.
    assert snapshot.pr_number is not None
    assert snapshot.occ_commit_sha is not None
    assert snapshot.contracts_dir is not None
    assert snapshot.receipts_dir is not None
    ticket_ids = tuple(_extract_ticket_ids(snapshot.pr_body, snapshot.pr_title))
    if not ticket_ids:
        return ModelOccEligibilityResult(
            eligible=False,
            reason=EnumOccEligibilityReason.MISSING_TICKET,
            occ_commit_sha=snapshot.occ_commit_sha,
            detail="PR title/body does not cite an OMN ticket",
        )

    for ticket_id in ticket_ids:
        if not _ticket_bound_to_pr(ticket_id, snapshot):
            return ModelOccEligibilityResult(
                eligible=False,
                reason=EnumOccEligibilityReason.PR_TICKET_MISMATCH,
                ticket_ids=ticket_ids,
                occ_commit_sha=snapshot.occ_commit_sha,
                detail=(
                    f"{ticket_id} is cited but not bound through PR title, branch, "
                    "commit text, or Evidence-Ticket metadata"
                ),
            )

    contract_hashes: dict[str, str] = {}
    contract_data_by_ticket: dict[str, object] = {}
    receipt_ids: list[str] = []
    missing_contracts: list[str] = []
    missing_receipts: list[str] = []
    nonpass_receipts: list[str] = []
    # OMN-19050: why the supersession guard refused a PASS or accepted one at
    # the same code. Carried into the verdict's detail so the reason a key
    # resolved as it did is in the log line, not only in the resolver.
    guard_notes: list[str] = []
    # OMN-16859: PENDING receipts on runner-covered check types, kept in their
    # own bucket so they can be reported distinctly ONLY when nothing harder is
    # outstanding. Deliberately a third list rather than a flag on
    # `nonpass_receipts`: the outranking rule below is then a plain ordering of
    # returns instead of a predicate someone can weaken by accident.
    awaiting_runner_receipts: list[str] = []
    # OMN-14404: stale contract bindings accumulate like every other failure
    # class in this function. Returning on the first one discards the other N-1
    # already-resolved receipts and costs the operator a full CI round per stale
    # receipt, which is what manufactured the #3965 -> #3966 -> #3968 -> #3969
    # serial OCC repair chain. Keys mirror `missing_or_nonpass_receipts`;
    # `stale_binding_details` holds the human-readable per-receipt message.
    stale_bindings: list[str] = []
    stale_binding_details: list[str] = []
    tickets_with_pr_bound_receipt: set[str] = set()

    def _stale_binding_result() -> ModelOccEligibilityResult:
        detail = "; ".join(stale_binding_details)
        if len(stale_bindings) > 1:
            detail = (
                f"{len(stale_bindings)} receipts have stale contract bindings "
                f"(repair all of them in one pass): {detail}"
            )
        return ModelOccEligibilityResult(
            eligible=False,
            reason=EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH,
            ticket_ids=ticket_ids,
            occ_commit_sha=snapshot.occ_commit_sha,
            contract_hashes=contract_hashes,
            receipt_ids=tuple(sorted(receipt_ids)),
            stale_receipt_bindings=tuple(sorted(stale_bindings)),
            detail=detail,
        )

    for ticket_id in ticket_ids:
        contract_path = snapshot.contracts_dir / f"{ticket_id}.yaml"
        if not contract_path.is_file():
            missing_contracts.append(ticket_id)
            continue
        try:
            contract_data = _load_yaml(contract_path)
            contract_hash = _sha256_file(contract_path)
        except (OSError, yaml.YAMLError) as exc:
            missing_contracts.append(ticket_id)
            # OMN-14404: a stale binding found in an earlier iteration still
            # dominates, exactly as it did when the binding check returned
            # inline. Same guard at every hard-fail return below; it can only
            # fire on bindings from PRIOR iterations, because the binding check
            # is the last check in an iteration and `continue`s on failure.
            if stale_bindings:
                return _stale_binding_result()
            return ModelOccEligibilityResult(
                eligible=False,
                reason=EnumOccEligibilityReason.MISSING_CONTRACT,
                ticket_ids=ticket_ids,
                occ_commit_sha=snapshot.occ_commit_sha,
                contract_hashes=contract_hashes,
                missing_contracts=tuple(sorted(missing_contracts)),
                detail=f"contract {contract_path} is unreadable: {exc}",
            )
        contract_hashes[ticket_id] = contract_hash
        contract_data_by_ticket[ticket_id] = contract_data
        triples = _iter_dod_evidence(contract_data)
        if not triples:
            missing_receipts.append(f"{ticket_id}:*:*")
            continue
        dod_evidence_raw = (
            contract_data.get("dod_evidence", [])
            if isinstance(contract_data, dict)
            else []
        )
        honestly_superseded = _honestly_superseded_dod_ids(dod_evidence_raw)
        for evidence_item_id, check_type, _check_value in triples:
            if evidence_item_id in honestly_superseded:
                # OMN-15664 AC5: a later dod_evidence item's evidence_artifact
                # honestly supersedes this one (see
                # _honestly_superseded_dod_ids docstring for the exact
                # honesty conditions). This item's own receipt requirement is
                # excused; it is not silently dropped from the contract, and
                # contract_compliance_check independently reports it WARN
                # "superseded" rather than executing its (possibly dead)
                # checks.
                continue
            receipt_path = (
                snapshot.receipts_dir
                / ticket_id
                / evidence_item_id
                / f"{check_type}.yaml"
            )
            receipt_key = f"{ticket_id}:{evidence_item_id}:{check_type}"

            # OMN-13888 (scope 3): resolve the supersession chain first. A
            # tombstone invalidates the key (no active receipt); a replacement
            # re-binds it to a net-new receipt without editing the base file.
            # OMN-16432: current_pr_number scopes resolution to the record
            # that explicitly targets this consumer when a shared key is
            # bound to several downstream PRs.
            supersession = resolve_supersession(
                snapshot.receipts_dir,
                ticket_id,
                evidence_item_id,
                check_type,
                current_pr_number=snapshot.pr_number,
            )
            if supersession is not None:
                if supersession.error is not None:
                    nonpass_receipts.append(receipt_key)
                    if stale_bindings:
                        return _stale_binding_result()
                    return ModelOccEligibilityResult(
                        eligible=False,
                        reason=EnumOccEligibilityReason.NONPASS_RECEIPT,
                        ticket_ids=ticket_ids,
                        occ_commit_sha=snapshot.occ_commit_sha,
                        contract_hashes=contract_hashes,
                        receipt_ids=tuple(sorted(receipt_ids)),
                        missing_or_nonpass_receipts=tuple(sorted(nonpass_receipts)),
                        detail=supersession.error,
                    )
                if supersession.guard_note is not None:
                    guard_notes.append(f"{receipt_key}: {supersession.guard_note}")
                if supersession.tombstoned or supersession.receipt is None:
                    missing_receipts.append(receipt_key)
                    continue
                receipt = supersession.receipt
                receipt_source = supersession.source_path
            else:
                if not receipt_path.exists():
                    missing_receipts.append(receipt_key)
                    continue
                try:
                    receipt_raw = _load_yaml(receipt_path)
                    receipt = ModelDodReceipt.model_validate(receipt_raw)
                except (OSError, yaml.YAMLError, ValidationError) as exc:
                    nonpass_receipts.append(receipt_key)
                    if stale_bindings:
                        return _stale_binding_result()
                    return ModelOccEligibilityResult(
                        eligible=False,
                        reason=EnumOccEligibilityReason.NONPASS_RECEIPT,
                        ticket_ids=ticket_ids,
                        occ_commit_sha=snapshot.occ_commit_sha,
                        contract_hashes=contract_hashes,
                        receipt_ids=tuple(sorted(receipt_ids)),
                        missing_or_nonpass_receipts=tuple(sorted(nonpass_receipts)),
                        detail=f"receipt {receipt_path} is invalid: {exc}",
                    )
                receipt_source = receipt_path
            if receipt.ticket_id != ticket_id:
                if stale_bindings:
                    return _stale_binding_result()
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.PR_TICKET_MISMATCH,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    detail=(
                        f"receipt {receipt_source} declares ticket_id={receipt.ticket_id}, "
                        f"expected {ticket_id}"
                    ),
                )
            is_bound = _receipt_bound_to_pr(receipt, snapshot)
            # OMN-13888 (scope 1/5): dual-accept contract binding. A receipt
            # with a per-entry hash is checked strictly; a legacy receipt is
            # whole-file-checked only when bound to THIS PR (prior merged
            # receipts grandfather so appending an entry does not invalidate
            # them). The None hard-fail (OMN-10421 / OMN-13061) fires only when
            # BOTH bindings are absent.
            #
            # Round-1 soft-spot (verifier PROBE6): `is_bound` keys on the
            # receipt-controlled `pr_number`, so a NEW legacy-only receipt could
            # in principle set a FOREIGN pr_number to reach the grandfather path
            # and skip the whole-file check with a wrong hash. That path is NOT
            # independently exploitable end-to-end: a receipt can only be
            # introduced through an onex_change_control PR, and OCC's Receipt
            # Honesty Gate (scripts/validation/check_receipt_hardening.py, a
            # REQUIRED status check) validates every post-cutoff receipt's
            # contract_sha256 == sha256(contracts/<ticket>.yaml) UNCONDITIONAL on
            # pr_number — so a forged wrong-hash net-new receipt is rejected
            # upstream before this grandfather is ever reached. The grandfather
            # here is defense-in-depth behind that stricter gate; the terminal
            # fix is the per-entry hash (scope 1), which makes every new receipt
            # immune to appends without needing the whole-file grandfather at
            # all. Full closure of the pure-function residual (an unforgeable
            # "receipt file is net-new in this PR" git signal threaded from CI)
            # is tracked as follow-up and is disproportionate to wire here.
            if (
                receipt.contract_sha256 is None
                and receipt.contract_entry_sha256 is None
            ):
                if stale_bindings:
                    return _stale_binding_result()
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    detail=(
                        f"receipt {receipt_source} missing both contract_sha256 and "
                        f"contract_entry_sha256 (OMN-10421 / OMN-13061 / OMN-13888): "
                        f"receipts produced after "
                        f"{_CONTRACT_SHA256_REQUIRED_AFTER.date()} must bind the "
                        "contract. Rerun probes to produce a new receipt."
                    ),
                )
            binding_error = check_receipt_contract_binding(
                receipt=receipt,
                contract_data=contract_data,
                evidence_item_id=evidence_item_id,
                whole_file_hash=contract_hash,
                is_bound_to_this_pr=is_bound,
            )
            if binding_error is not None:
                stale_bindings.append(receipt_key)
                stale_binding_details.append(
                    f"receipt {receipt_source}: {binding_error}"
                )
                continue
            if is_bound:
                tickets_with_pr_bound_receipt.add(ticket_id)
            if receipt.status is not EnumReceiptStatus.PASS:
                # OMN-16859: an honest PENDING on a check type a product-repo
                # runner executes is "not yet run", not "ran and failed". Both
                # are ineligible; only the remedy differs, and naming the wrong
                # remedy is what cost four lanes a full re-diagnosis each on
                # 2026-08-28. ADVISORY and FAIL are NOT included — ADVISORY
                # means the probe ran but the proof is structurally weak, and
                # FAIL means it ran and contradicted the claim; neither is
                # waiting on anything.
                if (
                    receipt.status is EnumReceiptStatus.PENDING
                    and check_type in RUNNER_COVERED_CHECK_TYPES
                    and is_bound
                ):
                    awaiting_runner_receipts.append(receipt_key)
                else:
                    nonpass_receipts.append(receipt_key)
                continue
            receipt_ids.append(receipt_key)

    # OMN-14404: stale bindings are reported FIRST, ahead of MISSING_CONTRACT,
    # MISSING_RECEIPT/NONPASS_RECEIPT and the terminal unbound-ticket check. This
    # reproduces the pre-batching precedence exactly: the old in-loop early return
    # preempted every one of those post-loop checks, in every iteration order.
    if stale_bindings:
        return _stale_binding_result()
    if missing_contracts:
        return ModelOccEligibilityResult(
            eligible=False,
            reason=EnumOccEligibilityReason.MISSING_CONTRACT,
            ticket_ids=ticket_ids,
            occ_commit_sha=snapshot.occ_commit_sha,
            contract_hashes=contract_hashes,
            receipt_ids=tuple(sorted(receipt_ids)),
            missing_contracts=tuple(sorted(missing_contracts)),
            detail="one or more ticket contracts are missing from pinned OCC evidence",
        )
    if missing_receipts or nonpass_receipts:
        reason = (
            EnumOccEligibilityReason.MISSING_RECEIPT
            if missing_receipts
            else EnumOccEligibilityReason.NONPASS_RECEIPT
        )
        return ModelOccEligibilityResult(
            eligible=False,
            reason=reason,
            ticket_ids=ticket_ids,
            occ_commit_sha=snapshot.occ_commit_sha,
            contract_hashes=contract_hashes,
            receipt_ids=tuple(sorted(receipt_ids)),
            missing_or_nonpass_receipts=tuple(
                sorted(
                    [
                        *missing_receipts,
                        *nonpass_receipts,
                        *awaiting_runner_receipts,
                    ]
                )
            ),
            detail=_with_guard_notes(
                "one or more receipts are missing or non-PASS", guard_notes
            ),
        )

    # OMN-18075: an OCC companion's receipt-to-current-PR binding is structural
    # provenance, not product DoD evidence. New companions therefore keep the
    # deterministic ``occ-self-bind-pr-<N>`` receipt but no longer declare that
    # id in ``dod_evidence`` (where it polluted the closer's probative ratio).
    # Resolve that one receipt directly, only for the canonical OCC repo and
    # only when declared evidence has not already bound the ticket. The latter
    # preserves every historical companion whose self-bind remains declared.
    if _is_occ_repo(snapshot.repo):
        for ticket_id in ticket_ids:
            if ticket_id in tickets_with_pr_bound_receipt:
                continue

            evidence_item_id = f"occ-self-bind-pr-{snapshot.pr_number}"
            receipt_key = (
                f"{ticket_id}:{evidence_item_id}:{_STRUCTURAL_SELF_BIND_CHECK_TYPE}"
            )
            receipt_path = (
                snapshot.contracts_dir.parent
                / _STRUCTURAL_BINDINGS_RELATIVE_DIR
                / ticket_id
                / evidence_item_id
                / f"{_STRUCTURAL_SELF_BIND_CHECK_TYPE}.yaml"
            )
            if not receipt_path.is_file():
                continue

            try:
                receipt_raw = _load_yaml(receipt_path)
                receipt = ModelDodReceipt.model_validate(receipt_raw)
            except (OSError, yaml.YAMLError, ValidationError) as exc:
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.NONPASS_RECEIPT,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    missing_or_nonpass_receipts=(receipt_key,),
                    detail=f"structural self-bind receipt {receipt_path} is invalid: {exc}",
                )

            expected_key = (
                ticket_id,
                evidence_item_id,
                _STRUCTURAL_SELF_BIND_CHECK_TYPE,
            )
            actual_key = (
                receipt.ticket_id,
                receipt.evidence_item_id,
                receipt.check_type,
            )
            if actual_key != expected_key:
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.PR_TICKET_MISMATCH,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    detail=(
                        f"structural self-bind receipt {receipt_path} declares key "
                        f"{actual_key!r}, expected {expected_key!r}"
                    ),
                )

            is_bound = _receipt_bound_to_pr(receipt, snapshot)
            if receipt.contract_entry_sha256 is not None:
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    stale_receipt_bindings=(receipt_key,),
                    detail=(
                        f"structural self-bind receipt {receipt_path} must not "
                        "declare contract_entry_sha256 because its evidence id "
                        "is intentionally absent from dod_evidence (OMN-18075)"
                    ),
                )
            if (
                receipt.contract_sha256 is None
                and receipt.contract_entry_sha256 is None
            ):
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    stale_receipt_bindings=(receipt_key,),
                    detail=(
                        f"structural self-bind receipt {receipt_path} is missing "
                        "both contract_sha256 and contract_entry_sha256"
                    ),
                )
            binding_error = check_receipt_contract_binding(
                receipt=receipt,
                contract_data=contract_data_by_ticket[ticket_id],
                evidence_item_id=evidence_item_id,
                whole_file_hash=contract_hashes[ticket_id],
                is_bound_to_this_pr=is_bound,
            )
            if binding_error is not None:
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    stale_receipt_bindings=(receipt_key,),
                    detail=f"structural self-bind receipt {receipt_path}: {binding_error}",
                )
            if receipt.status is not EnumReceiptStatus.PASS:
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.NONPASS_RECEIPT,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    missing_or_nonpass_receipts=(receipt_key,),
                    detail=(
                        f"structural self-bind receipt {receipt_path} has "
                        f"non-PASS status {receipt.status.value}"
                    ),
                )

            receipt_ids.append(receipt_key)
            if is_bound:
                tickets_with_pr_bound_receipt.add(ticket_id)

    unbound_tickets = tuple(
        ticket_id
        for ticket_id in ticket_ids
        if ticket_id not in tickets_with_pr_bound_receipt
    )
    if unbound_tickets:
        if _is_occ_repo(snapshot.repo):
            # OMN-16353: reaching this branch means every contract resolved and
            # every required receipt is PASS and hash-bound — the ONLY defect is
            # that no receipt binds to THIS PR. On the OCC repo itself that is
            # the hand-authored-companion omission of the self-bind entry
            # (three occurrences in one 2026-08-21 session: OCC#6819, #6820,
            # #6675). The verdict is unchanged (ineligible either way);
            # only the reason and remediation differ — advisory-to-actionable.
            return ModelOccEligibilityResult(
                eligible=False,
                reason=EnumOccEligibilityReason.MISSING_OCC_SELF_BIND,
                ticket_ids=ticket_ids,
                occ_commit_sha=snapshot.occ_commit_sha,
                contract_hashes=contract_hashes,
                receipt_ids=tuple(sorted(receipt_ids)),
                detail="\n\n".join(
                    _self_bind_remediation(ticket_id, snapshot.pr_number)
                    for ticket_id in unbound_tickets
                ),
            )
        return ModelOccEligibilityResult(
            eligible=False,
            reason=EnumOccEligibilityReason.PR_TICKET_MISMATCH,
            ticket_ids=ticket_ids,
            occ_commit_sha=snapshot.occ_commit_sha,
            contract_hashes=contract_hashes,
            receipt_ids=tuple(sorted(receipt_ids)),
            detail=(
                "no PASS receipt for one or more tickets binds to PR "
                f"#{snapshot.pr_number} or one of its commit SHAs: "
                f"{', '.join(unbound_tickets)}"
            ),
        )

    # OMN-16859 — DELIBERATELY AFTER the missing/non-PASS and unbound-ticket
    # returns above.
    #
    # That ordering IS the safety property, and it is why this is a legibility
    # split rather than a carve-out: a genuinely absent receipt or a receipt
    # that ran and FAILED is reported as such and reaches its own return first.
    # This branch can only be taken when every other declared receipt resolved
    # PASS and the sole outstanding item is an honestly-PENDING one on a check
    # type a product-repo runner executes. Moving this block above that one
    # would let "not yet run" mask "ran and failed"; do not reorder.
    #
    # The verdict is unchanged from before this ticket (`eligible=False`), and
    # the key is still surfaced in `missing_or_nonpass_receipts` so CI logs and
    # downstream tooling that read that field do not go blind on the new reason.
    if awaiting_runner_receipts:
        return ModelOccEligibilityResult(
            eligible=False,
            reason=EnumOccEligibilityReason.AWAITING_RUNNER_RECEIPT,
            ticket_ids=ticket_ids,
            occ_commit_sha=snapshot.occ_commit_sha,
            contract_hashes=contract_hashes,
            receipt_ids=tuple(sorted(receipt_ids)),
            missing_or_nonpass_receipts=tuple(sorted(awaiting_runner_receipts)),
            detail=(
                f"{len(awaiting_runner_receipts)} receipt(s) are honestly PENDING "
                "on a check type the OCC producers cannot execute (they run in "
                "the .201 effects runtime with no product checkout): "
                f"{', '.join(sorted(awaiting_runner_receipts))}. This is NOT a "
                "missing receipt and NOT a failed check — the probe was "
                "allocated and has not run yet. The product repo's OCC receipt "
                "runner executes the declared check at PR head and appends a "
                "superseding receipt to this companion's branch; preflight then "
                "re-evaluates. Do NOT hand-author a receipt to clear this: "
                "check the product PR's OCC receipt runner job first, and fix "
                "it if it did not run. Merge stays blocked until a real "
                "executed PASS supersedes the PENDING receipt "
                f"(runner-covered check types: {', '.join(sorted(RUNNER_COVERED_CHECK_TYPES))})."
            ),
        )
    return ModelOccEligibilityResult(
        eligible=True,
        reason=EnumOccEligibilityReason.ELIGIBLE,
        ticket_ids=ticket_ids,
        occ_commit_sha=snapshot.occ_commit_sha,
        contract_hashes=contract_hashes,
        receipt_ids=tuple(sorted(receipt_ids)),
        detail=_with_guard_notes(
            "OCC evidence is present, PASS, hash-bound, and PR-bound", guard_notes
        ),
    )


def _with_guard_notes(detail: str, guard_notes: list[str]) -> str:
    if not guard_notes:
        return detail
    return f"{detail}; supersession guard: " + "; ".join(guard_notes)


def _read_file(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OCC-first merge eligibility gate")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--pr-title", required=True)
    parser.add_argument("--pr-body", default=None)
    parser.add_argument("--pr-body-file", default=None)
    parser.add_argument("--pr-branch", required=True)
    parser.add_argument("--pr-commit-sha", action="append", default=[])
    parser.add_argument("--pr-commit-text", action="append", default=[])
    parser.add_argument("--occ-commit-sha", required=True)
    parser.add_argument("--contracts-dir", required=True)
    parser.add_argument("--receipts-dir", required=True)
    args = parser.parse_args(argv)

    body = args.pr_body if args.pr_body is not None else _read_file(args.pr_body_file)
    snapshot = ModelOccEligibilityInput(
        repo=args.repo,
        pr_number=args.pr_number,
        pr_title=args.pr_title,
        pr_body=body,
        pr_branch=args.pr_branch,
        pr_commit_shas=tuple(args.pr_commit_sha),
        pr_commit_texts=tuple(args.pr_commit_text),
        occ_commit_sha=args.occ_commit_sha,
        contracts_dir=Path(args.contracts_dir),
        receipts_dir=Path(args.receipts_dir),
    )
    result = validate_occ_merge_eligibility(snapshot)
    sys.stdout.write(f"{result.to_json()}\n")
    return 0 if result.eligible else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "EnumOccEligibilityReason",
    "ModelOccEligibilityInput",
    "ModelOccEligibilityResult",
    "validate_occ_merge_eligibility",
]
