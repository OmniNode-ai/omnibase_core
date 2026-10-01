# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical digest helpers for trusted goal verification."""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.work.model_work_ruling_recorded import (
    ModelWorkRulingRecorded,
)


def compute_goal_resolution_event_sha256(event: ModelWorkRulingRecorded) -> str:
    """Digest the canonical typed Work Ledger ruling payload."""
    canonical = json.dumps(
        event.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def compute_goal_execution_request_sha256(
    *,
    repository: str,
    goal_id: UUID,
    contract_revision: UUID,
    contract_sha256: str,
    policy_revision: UUID,
    verifier_artifact_sha256: str,
    criterion_baseline_sha256: str,
    revision_history_sha256: str,
    evaluation_observation_sha256: str,
    subject_manifest_sha256: str,
    attempt_id: UUID,
    attempt_sequence: int,
    subject_kind: str,
    subject_commit_sha: str,
    subject_tree_sha: str,
) -> str:
    """Digest the immutable execution plan before a RUNNING snapshot exists.

    The allocation snapshot and this digest itself are deliberately excluded.
    A separate signed execution receipt binds the actual RUNNING snapshot, which
    avoids a circular digest over a store row containing this value.
    """
    if subject_kind not in {"commit", "merge_group", "deployment"}:
        raise ModelOnexError(
            "subject_kind must be commit, merge_group, or deployment",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    payload = {
        "repository": repository,
        "goal_id": str(goal_id),
        "contract_revision": str(contract_revision),
        "contract_sha256": contract_sha256,
        "policy_revision": str(policy_revision),
        "verifier_artifact_sha256": verifier_artifact_sha256,
        "criterion_baseline_sha256": criterion_baseline_sha256,
        "revision_history_sha256": revision_history_sha256,
        "evaluation_observation_sha256": evaluation_observation_sha256,
        "subject_manifest_sha256": subject_manifest_sha256,
        "attempt_id": str(attempt_id),
        "attempt_sequence": attempt_sequence,
        "subject_kind": subject_kind,
        "subject_commit_sha": subject_commit_sha,
        "subject_tree_sha": subject_tree_sha,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
