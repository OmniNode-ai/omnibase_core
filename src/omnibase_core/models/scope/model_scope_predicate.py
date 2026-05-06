# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelScopePredicate — per-artifact applicability predicate vocabulary.

Used in ModelApplicabilityScope.applies_when and disabled_when fields.
Conflict resolution: disabled_when always wins over applies_when when both
match for the same predicate key.

Predicate vocabulary is intentionally extensible: all fields are Optional so
that new predicates can be added to the schema without breaking existing YAML
files. The overlay loader (OMN-9905) merges predicates by union of keys; a
key present in both base and overlay takes the overlay value.

Predicate semantics:
    cwd_in:       Match cwd against named EnumScopeToken topology classes.
                  Evaluated by the scope registry, not by string comparison.
    repo:         Match repository kind (omninode, external, etc.).
    ticket:       Match the current Linear ticket namespace.
    state:        Match required runtime state markers (env vars, dirs).
    integrations: Match availability of named integrations (linear, kafka).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_scope_token import EnumScopeToken
from omnibase_core.models.scope.model_integration_filter import ModelIntegrationFilter
from omnibase_core.models.scope.model_repo_filter import ModelRepoFilter
from omnibase_core.models.scope.model_state_filter import ModelStateFilter
from omnibase_core.models.scope.model_ticket_filter import ModelTicketFilter


class ModelScopePredicate(BaseModel):
    """
    Applicability predicate for a hook or skill scope declaration.

    Used in ``applies_when`` and ``disabled_when`` within
    :class:`~omnibase_core.models.scope.model_applicability_scope.ModelApplicabilityScope`.
    All fields are optional — an empty predicate matches universally.

    Conflict resolution:
        When ``disabled_when`` and ``applies_when`` both produce a match for
        the same artifact invocation, ``disabled_when`` wins unconditionally.
        This ensures explicit opt-outs always take precedence.

    Overlay semantics (OMN-9905):
        Predicates from an overlay are merged by key union. A key present in
        both base and overlay takes the overlay value. New keys introduced by
        an overlay extend (not replace) the base predicate.

    Attributes:
        cwd_in:       Match cwd against named topology class tokens.
        repo:         Match repository kind.
        ticket:       Match the current Linear ticket namespace.
        state:        Match required runtime state markers.
        integrations: Match availability of named integrations.

    Example YAML surface (illustrative):

    .. code-block:: yaml

        applies_when:
          cwd_in: [omninode_repo]
          repo:
            kind: omninode
          ticket:
            namespace: OMN
          state:
            requires: [ONEX_STATE_DIR, evidence_dir]
          integrations:
            linear:
              workspace: omninode
              ticket_prefix: OMN
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    cwd_in: list[EnumScopeToken] = Field(
        default_factory=list,
        description=(
            "Match cwd against these named topology class tokens. "
            "Empty list matches universally. Evaluated by the scope registry."
        ),
    )
    repo: ModelRepoFilter | None = Field(
        default=None,
        description="Match repository kind. None matches universally.",
    )
    ticket: ModelTicketFilter | None = Field(
        default=None,
        description="Match the current Linear ticket namespace. None matches universally.",
    )
    state: ModelStateFilter | None = Field(
        default=None,
        description="Match required runtime state markers. None matches universally.",
    )
    integrations: ModelIntegrationFilter | None = Field(
        default=None,
        description="Match availability of named integrations. None matches universally.",
    )

    def is_universal(self) -> bool:
        """Return True if all predicate fields are empty/None (matches everything)."""
        return (
            not self.cwd_in
            and self.repo is None
            and self.ticket is None
            and self.state is None
            and self.integrations is None
        )


__all__ = ["ModelScopePredicate"]
