# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelApplicabilityScope — per-artifact applies_when / disabled_when gate.

Determines whether a hook or skill applies to the current repo, session,
or tool event. Evaluated per-invocation, after the plugin has been activated.

Conflict resolution: disabled_when always wins over applies_when when both
predicates match simultaneously.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.scope.model_scope_predicate import ModelScopePredicate


class ModelApplicabilityScope(BaseModel):
    """
    Per-artifact applicability gate (applies_when / disabled_when).

    Determines whether a hook or skill applies to the current repo, session,
    or tool event. Evaluated per-invocation, after the plugin has been
    activated.

    Conflict resolution:
        ``disabled_when`` **always wins** over ``applies_when`` when both
        predicates match simultaneously. An explicit opt-out always takes
        precedence over an opt-in.

    Overlay semantics (OMN-9905):
        Overlay applicability scopes are merged by predicate key union.
        ``applies_when`` keys from the overlay extend the base; conflicting
        keys take the overlay value. ``disabled_when`` follows the same rule.
        The disabled-wins conflict rule applies to the merged result.

    Attributes:
        applies_when:  Predicate that must match for this artifact to apply.
                       Empty predicate (default) matches universally.
        disabled_when: Predicate that, when matching, suppresses this artifact.
                       Takes precedence over applies_when on conflict.

    See Also:
        - :class:`~omnibase_core.models.scope.model_scope_predicate.ModelScopePredicate`:
          Predicate vocabulary (cwd_in, repo, ticket, state, integrations).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    applies_when: ModelScopePredicate = Field(
        default_factory=ModelScopePredicate,
        description=(
            "Predicate that must match for this artifact to apply. "
            "An empty predicate matches universally (default behaviour)."
        ),
    )
    disabled_when: ModelScopePredicate = Field(
        default_factory=ModelScopePredicate,
        description=(
            "Predicate that, when matching, suppresses this artifact. "
            "disabled_when wins over applies_when on any conflict."
        ),
    )


__all__ = ["ModelApplicabilityScope"]
