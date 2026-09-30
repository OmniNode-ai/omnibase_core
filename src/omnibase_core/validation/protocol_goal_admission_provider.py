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
    from omnibase_core.models.validation.model_goal_attempt_allocation_snapshot import (
        ModelGoalAttemptAllocationSnapshot,
    )
    from omnibase_core.models.validation.model_goal_dependency_proof_pin import (
        ModelGoalDependencyProofPin,
    )
    from omnibase_core.models.validation.model_goal_evaluation_observation import (
        ModelGoalEvaluationObservation,
    )
    from omnibase_core.models.validation.model_goal_mutation_state import (
        ModelGoalMutationState,
    )
    from omnibase_core.models.validation.model_goal_revision_history_snapshot import (
        ModelGoalRevisionHistorySnapshot,
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
    ) -> tuple[ModelGoalSupervisorAttestation, ModelGoalEvaluationObservation] | None:
        """Read exact protected signed evidence for one declared dependency pin."""
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
