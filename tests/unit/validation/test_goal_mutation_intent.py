# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Goal mutation barriers retain every competing contract revision."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from omnibase_core.models.validation.model_goal_mutation_confirmation import (
    ModelGoalMutationConfirmation,
)
from omnibase_core.models.validation.model_goal_mutation_context import (
    ModelGoalMutationContext,
)
from omnibase_core.models.validation.model_goal_mutation_intent import (
    ModelGoalMutationIntent,
)
from omnibase_core.models.validation.model_goal_mutation_revision import (
    ModelGoalMutationRevision,
)
from omnibase_core.models.validation.model_goal_mutation_scope_absence_proof import (
    ModelGoalMutationScopeAbsenceProof,
)


def _context(
    *, head_sha: str, contract_revision: UUID, check_run_id: str
) -> ModelGoalMutationContext:
    return ModelGoalMutationContext(
        app_integration_id="github-app-17",
        context_name="Verifier / goal-admission",
        head_sha=head_sha,
        contract_revision=contract_revision,
        attempt_id=UUID(int=int(check_run_id)),
        attempt_sequence=1,
        check_run_id=check_run_id,
        external_id=f"goal:{head_sha}",
        request_sha256="sha256:" + "a" * 64,
    )


def _intent(
    *,
    current_contract_revisions: tuple[ModelGoalMutationRevision, ...],
    affected_contexts: tuple[ModelGoalMutationContext, ...],
    current_contract_revision: UUID | None = None,
    current_contract_sha256: str | None = None,
) -> ModelGoalMutationIntent:
    return ModelGoalMutationIntent(
        intent_id=UUID(int=10),
        nonce=UUID(int=11),
        repository="omninode-ai/omnibase_core",
        goal_id=UUID(int=12),
        mutation_kind="contract_revision",
        app_integration_id="github-app-17",
        required_context_name="Verifier / goal-admission",
        current_contract_revision=current_contract_revision,
        current_contract_sha256=current_contract_sha256,
        current_contract_revisions=current_contract_revisions,
        proposed_contract_revision=UUID(int=13),
        proposed_contract_sha256="sha256:" + "b" * 64,
        proposed_policy_revision=UUID(int=14),
        proposed_policy_sha256="sha256:" + "c" * 64,
        history_store_revision=UUID(int=15),
        policy_store_revision=UUID(int=16),
        observation_store_revision=UUID(int=17),
        attempt_store_revision=UUID(int=18),
        publication_store_revision=UUID(int=19),
        affected_contexts=affected_contexts,
        affected_head_shas=tuple(context.head_sha for context in affected_contexts),
        created_at=datetime(2026, 9, 30, tzinfo=UTC),
    )


def test_fork_mutation_intent_binds_each_issued_context_to_its_revision() -> None:
    first_revision = UUID(int=20)
    second_revision = UUID(int=21)
    contexts = (
        _context(
            head_sha="1" * 40,
            contract_revision=first_revision,
            check_run_id="101",
        ),
        _context(
            head_sha="2" * 40,
            contract_revision=second_revision,
            check_run_id="102",
        ),
    )

    intent = _intent(
        current_contract_revisions=(
            ModelGoalMutationRevision(
                revision_id=second_revision, contract_sha256="sha256:" + "e" * 64
            ),
            ModelGoalMutationRevision(
                revision_id=first_revision, contract_sha256="sha256:" + "d" * 64
            ),
        ),
        affected_contexts=contexts,
    )

    assert len(intent.current_contract_revisions) == 2
    assert intent.content_sha256().startswith("sha256:")


def test_fork_mutation_intent_rejects_context_outside_competing_revisions() -> None:
    contexts = (
        _context(
            head_sha="1" * 40,
            contract_revision=UUID(int=20),
            check_run_id="101",
        ),
        _context(
            head_sha="2" * 40,
            contract_revision=UUID(int=22),
            check_run_id="102",
        ),
    )

    with pytest.raises(ValidationError, match="affected context does not match"):
        _intent(
            current_contract_revisions=(
                ModelGoalMutationRevision(
                    revision_id=UUID(int=20),
                    contract_sha256="sha256:" + "d" * 64,
                ),
                ModelGoalMutationRevision(
                    revision_id=UUID(int=21),
                    contract_sha256="sha256:" + "e" * 64,
                ),
            ),
            affected_contexts=contexts,
        )


def test_fork_mutation_intent_requires_unique_competing_members() -> None:
    revision = ModelGoalMutationRevision(
        revision_id=UUID(int=20), contract_sha256="sha256:" + "d" * 64
    )
    context = _context(
        head_sha="1" * 40,
        contract_revision=revision.revision_id,
        check_run_id="101",
    )

    with pytest.raises(ValidationError, match="must contain a fork"):
        _intent(current_contract_revisions=(revision,), affected_contexts=(context,))


def test_empty_owned_scope_requires_a_matching_protected_inventory_proof() -> None:
    intent = _intent(current_contract_revisions=(), affected_contexts=())
    proof = ModelGoalMutationScopeAbsenceProof(
        repository=intent.repository,
        goal_id=intent.goal_id,
        intent_id=intent.intent_id,
        app_integration_id=intent.app_integration_id,
        required_context_name=intent.required_context_name,
        publication_store_revision=intent.publication_store_revision,
        attempt_store_revision=intent.attempt_store_revision,
        attempt_subject_count=0,
        journal_context_count=0,
        unresolved_publication_intent_count=0,
        captured_at=datetime(2026, 9, 30, tzinfo=UTC),
    )
    confirmation_values = {
        "intent_id": intent.intent_id,
        "intent_sha256": intent.content_sha256(),
        "intent": intent,
        "repository": intent.repository,
        "goal_id": intent.goal_id,
        "outcome": "complete_absence",
        "issued_contexts": (),
        "readbacks": (),
        "absence_proofs": (),
        "scope_absence_proof": proof,
        "confirmed_at": datetime(2026, 9, 30, tzinfo=UTC),
    }
    provisional = ModelGoalMutationConfirmation.model_construct(
        **confirmation_values, confirmation_sha256="sha256:" + "0" * 64
    )
    confirmation = ModelGoalMutationConfirmation(
        **confirmation_values,
        confirmation_sha256=provisional.content_sha256(),
    )

    assert confirmation.scope_absence_proof == proof
    assert confirmation.intent.affected_head_shas == ()


def test_empty_owned_scope_without_inventory_proof_is_rejected() -> None:
    intent = _intent(current_contract_revisions=(), affected_contexts=())
    with pytest.raises(ValidationError, match="empty goal scope"):
        ModelGoalMutationConfirmation(
            intent_id=intent.intent_id,
            intent_sha256=intent.content_sha256(),
            intent=intent,
            repository=intent.repository,
            goal_id=intent.goal_id,
            outcome="complete_absence",
            issued_contexts=(),
            readbacks=(),
            absence_proofs=(),
            confirmed_at=datetime(2026, 9, 30, tzinfo=UTC),
            confirmation_sha256="sha256:" + "0" * 64,
        )
