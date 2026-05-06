# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelEnforcementScope — top-level scope contract for hooks and skills.

This is the primary model that hooks and skills declare in their YAML
contracts to describe their scope. It makes the activation / applicability /
enforcement triad first-class: each is a separate sub-model with its own
semantics, rather than a collapsed "is the plugin installed?" boolean.

Triad semantics:
    Activation  — manifest-level. Should the plugin load at all this session?
                  Evaluated once at session start. (ModelActivationScope)
    Applicability — per-artifact. Does this hook/skill apply to this
                  repo/session/tool-event? (ModelApplicabilityScope)
    Enforcement — per-artifact. What happens when the artifact is applicable
                  and a scope condition fires? (ModelArtifactEnforcement)

Today the three collapse into "is the plugin installed?" — this schema
corrects that by making each independently contract-addressable.

Hook YAML example:

.. code-block:: yaml

    hook:
      id: pre_tool_use_dispatch_guard_ticket_evidence
      event: PreToolUse
      scope:
        activation:
          requires_tokens: [omninode_repo]
        applicability:
          applies_when:
            repo:
              kind: omninode
            ticket:
              namespace: OMN
            state:
              requires: [ONEX_STATE_DIR, evidence_dir]
          disabled_when:
            repo:
              kind: external
        enforcement:
          default: block
          non_matching_scope: observe
          missing_dependency: observe
      unavailable_behavior:
        default: hidden
        diagnostics: explain

Skill YAML example:

.. code-block:: yaml

    skill:
      id: create_ticket
      scope:
        activation:
          requires_tokens: [omninode_repo]
        applicability:
          applies_when:
            integrations:
              linear:
                workspace: omninode
                ticket_prefix: OMN
        enforcement:
          default: warn
      unavailable_behavior:
        default: hidden
        diagnostics: explain
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.scope.model_activation_scope import ModelActivationScope
from omnibase_core.models.scope.model_applicability_scope import ModelApplicabilityScope
from omnibase_core.models.scope.model_artifact_enforcement import (
    ModelArtifactEnforcement,
)
from omnibase_core.models.scope.model_unavailable_behavior import (
    ModelUnavailableBehavior,
)


class ModelEnforcementScope(BaseModel):
    """
    Top-level scope contract for ONEX hooks and skills.

    Embeds the full activation / applicability / enforcement triad as
    first-class sub-models. This is the model that hook and skill YAML
    contracts reference in their ``scope:`` block.

    Triad semantics:
        **Activation** (:class:`~omnibase_core.models.scope.model_activation_scope.ModelActivationScope`):
            Should the plugin load at all for this session? Manifest-level,
            coarse-grained. Evaluated once by the overlay loader at session
            start. A plugin that fails activation is not registered at all.

        **Applicability** (:class:`~omnibase_core.models.scope.model_applicability_scope.ModelApplicabilityScope`):
            Does this specific hook or skill apply to the current invocation
            context? Per-artifact, fine-grained. Evaluated per-tool-use or
            per-invocation. ``disabled_when`` wins over ``applies_when`` on
            conflict.

        **Enforcement** (:class:`~omnibase_core.models.scope.model_artifact_enforcement.ModelArtifactEnforcement`):
            What outcome occurs when the artifact is applicable and a scope
            condition fires? Per-artifact. Supports differentiated tiers for
            matching vs. non-matching vs. missing-dependency paths.

    Skills additionally declare ``unavailable_behavior`` to control what
    users see when the skill's scope is not satisfied (OMN-9895).

    Overlay loader composition (OMN-9905):
        Base scope + overlay scope -> merged scope. Overlays may narrow
        applicability predicates, downgrade enforcement tiers, and change
        unavailable_behavior. They cannot introduce new activation requirements
        that were absent from the base without a coordinated base update.

    Attributes:
        activation:          Manifest-level plugin load gate.
        applicability:       Per-artifact applies_when / disabled_when predicates.
        enforcement:         Per-artifact enforcement tier configuration.
        unavailable_behavior: How skills present when scope is not satisfied.
                              Not applicable to hooks (hooks are simply skipped).

    See Also:
        - :class:`~omnibase_core.models.scope.model_activation_scope.ModelActivationScope`
        - :class:`~omnibase_core.models.scope.model_applicability_scope.ModelApplicabilityScope`
        - :class:`~omnibase_core.models.scope.model_artifact_enforcement.ModelArtifactEnforcement`
        - :class:`~omnibase_core.models.scope.model_unavailable_behavior.ModelUnavailableBehavior`
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    activation: ModelActivationScope = Field(
        default_factory=ModelActivationScope,
        description=(
            "Manifest-level plugin load gate. Evaluated once at session start. "
            "A plugin that fails activation is not registered."
        ),
    )
    applicability: ModelApplicabilityScope = Field(
        default_factory=ModelApplicabilityScope,
        description=(
            "Per-artifact applies_when / disabled_when predicates. "
            "disabled_when wins over applies_when on conflict."
        ),
    )
    enforcement: ModelArtifactEnforcement = Field(
        default_factory=ModelArtifactEnforcement,
        description=(
            "Per-artifact enforcement tier. Overlays may downgrade (never upgrade) "
            "enforcement tiers without operator-level intent."
        ),
    )
    unavailable_behavior: ModelUnavailableBehavior = Field(
        default_factory=ModelUnavailableBehavior,
        description=(
            "How skills present when scope is not satisfied. "
            "Not applicable to hooks (hooks are simply skipped when not applicable)."
        ),
    )


__all__ = ["ModelEnforcementScope"]
