# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protected policy, key and attestation lookup for goal admission."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.validation.protocol_goal_work_ledger_key_provider import (
    ProtocolGoalWorkLedgerKeyProvider,
)

if TYPE_CHECKING:
    from omnibase_core.models.validation.model_goal_admission_observation import (
        ModelGoalAdmissionObservation,
    )
    from omnibase_core.models.validation.model_goal_attempt_allocation_snapshot import (
        ModelGoalAttemptAllocationSnapshot,
    )
    from omnibase_core.models.validation.model_goal_commit_source_readback import (
        ModelGoalCommitSourceReadback,
    )
    from omnibase_core.models.validation.model_goal_dependency_admission_evidence import (
        ModelGoalDependencyAdmissionEvidence,
    )
    from omnibase_core.models.validation.model_goal_dependency_proof_pin import (
        ModelGoalDependencyProofPin,
    )
    from omnibase_core.models.validation.model_goal_evaluation_observation import (
        ModelGoalEvaluationObservation,
    )
    from omnibase_core.models.validation.model_goal_merge_group_source_readback import (
        ModelGoalMergeGroupSourceReadback,
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
    from omnibase_core.models.validation.model_goal_verifier_policy import (
        ModelGoalVerifierPolicy,
    )


@runtime_checkable
class ProtocolGoalAdmissionProvider(Protocol):
    """Resolve trust data from an independently configured protected source.

    Implementations must not source policy, keys or attestations from the
    candidate PR, contract body, receipt directory, or lifecycle command.
    Missing or revoked trust material is a fail-closed admission result.
    Implementations wrap backend failures as ``GoalAdmissionProviderError``.
    """

    def read_current_attempt_snapshot(
        self,
        *,
        repository: str,
        goal_id: UUID,
        contract_revision: UUID,
        subject_commit_sha: str,
        subject_tree_sha: str,
    ) -> ModelGoalAttemptAllocationSnapshot | None:
        """Read the complete current subject partition from trusted storage."""
        ...

    def read_current_goal_mutation_state(
        self, *, repository: str, goal_id: UUID
    ) -> ModelGoalMutationState | None:
        """Read protected App/history mutation barrier state for this goal.

        The backing implementation must establish its own authenticated App
        readbacks and complete scope inventory. A model supplied by a caller is
        not authority. Pending, sent, uncertain, and confirmed-but-not-activated
        intents remain blocking.
        """
        ...

    def get_policy(
        self,
        *,
        repository: str,
        goal_id: UUID,
        contract_revision: UUID,
    ) -> ModelGoalVerifierPolicy | None:
        """Return the active protected verifier policy for the exact goal."""
        ...

    def get_attestation(
        self,
        *,
        repository: str,
        goal_id: UUID,
        contract_revision: UUID,
        subject_commit_sha: str,
        subject_tree_sha: str,
        attempt_id: UUID,
        attempt_sequence: int,
        store_revision: UUID,
    ) -> ModelGoalSupervisorAttestation | None:
        """Return supervisor evidence bound to the current selected attempt."""
        ...

    def get_execution_receipt(
        self,
        *,
        repository: str,
        goal_id: UUID,
        contract_revision: UUID,
        subject_commit_sha: str,
        subject_tree_sha: str,
        attempt_id: UUID,
        attempt_sequence: int,
    ) -> ModelGoalSupervisorExecutionReceipt | None:
        """Return the signed immutable result from the isolated executor."""
        ...

    def get_dependency_evidence(
        self, *, dependency: ModelGoalDependencyProofPin
    ) -> ModelGoalDependencyAdmissionEvidence | None:
        """Read the current complete protected proof for one dependency pin."""
        ...

    def read_current_admission_observation(
        self,
        *,
        attempts: ModelGoalAttemptAllocationSnapshot,
        policy: ModelGoalVerifierPolicy,
        observation: ModelGoalEvaluationObservation,
        execution_receipt: ModelGoalSupervisorExecutionReceipt,
        attestation: ModelGoalSupervisorAttestation,
    ) -> ModelGoalAdmissionObservation | None:
        """Read the current protected post-run observation of this exact proof.

        The returned observation must be a fresh read from trusted admission
        storage on every call, bound to the supplied signed attempt, policy,
        initial deadline, execution receipt and supervisor attestation. Persist the
        exact canonical payload durably before returning it; its content digest is
        the retrieval key for replay. A cached or candidate-supplied timestamp is
        not authority.
        """
        ...

    def get_evaluation_observation(
        self,
        *,
        repository: str,
        goal_id: UUID,
        contract_revision: UUID,
        subject_commit_sha: str,
        subject_tree_sha: str,
    ) -> ModelGoalEvaluationObservation | None:
        """Read protected recorded evaluation/deadline events for this subject."""
        ...

    def read_current_commit_source(
        self,
        *,
        repository: str,
        goal_id: UUID,
        contract_revision: UUID,
        manifest: ModelGoalSubjectManifest,
        pull_request_number: int | None,
    ) -> ModelGoalCommitSourceReadback | None:
        """Read the current authenticated PR/branch source selected by policy.

        For a PR, the readback binds the exact current head repository/ref/SHA/tree
        and exact base repository/ref. For a branch, it reads the protected
        repository's exact current ``refs/heads/...`` value. Implementations must
        perform a fresh source read on every admission call; an old stored ref
        observation alone is not current-source evidence.
        """
        ...

    def read_current_merge_group_source(
        self,
        *,
        repository: str,
        goal_id: UUID,
        contract_revision: UUID,
        observation: ModelGoalEvaluationObservation,
    ) -> ModelGoalMergeGroupSourceReadback | None:
        """Revalidate a retained delivery and freshly read its current group.

        Implementations select the immutable retained webhook by the exact
        ``observation.merge_group_delivery_id``, verify original HMAC and
        broker checkpoint, bind repository/goal/revision/group and all source
        facts to the observation, then read current GitHub group refs, SHAs and
        trees. A stale, missing, unverified, or changed delivery is unavailable
        or mismatched; the stored observation alone is never current-source
        authority.
        """
        ...

    def read_current_revision_history(
        self,
        *,
        repository: str,
        goal_id: UUID,
    ) -> ModelGoalRevisionHistorySnapshot | None:
        """Read the complete trusted revision graph and fork-resolution history.

        Fork-resolution records must include the exact typed ruling event and
        its canonical digest. The implementation must authenticate the event
        from the accepted Work Ledger source and provide the immutable
        authorization policy revision named by that event. Core independently
        checks that the event payload matches the selected heads and that its
        actor is permitted by the returned policy; IDs, hashes, and event
        payloads supplied by a candidate are never authority.
        """
        ...

    def get_domain_trust_root(self, domain_id: str) -> bytes | None:
        """Return the currently trusted Ed25519 key for an issuer domain."""
        ...

    def get_work_ledger_key_provider(self) -> ProtocolGoalWorkLedgerKeyProvider | None:
        """Return the protected runtime-key provider for signed Work Ledger events.

        The provider must be populated from trusted runtime identity configuration,
        never from the Work Ledger event, goal contract, or candidate repository.
        """
        ...

    def read_artifact_bytes(self, digest: str) -> bytes | None:
        """Read a retained artifact by digest so its bytes can be rehashed."""
        ...


__all__ = ["ProtocolGoalAdmissionProvider"]
