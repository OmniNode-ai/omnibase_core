# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Scope contract schema for ONEX hooks and skills (OMN-9904).

Defines the activation / applicability / enforcement triad that makes
per-artifact scope declarations first-class in the contract system.

Enums live in omnibase_core.enums.*; models live here.

Public surface:
    ModelActivationScope      — manifest-level plugin load gate
    ModelApplicabilityScope   — per-artifact applies_when / disabled_when
    ModelArtifactEnforcement  — per-artifact enforcement tier config
    ModelEnforcementScope     — top-level scope contract (triad)
    ModelIntegrationFilter    — integration predicate filter
    ModelRepoFilter           — repo-kind predicate filter
    ModelScopePredicate       — full predicate vocabulary
    ModelStateFilter          — state marker predicate filter
    ModelTicketFilter         — ticket namespace predicate filter
    ModelUnavailableBehavior  — skill unavailability presentation contract
"""

from omnibase_core.models.scope.model_activation_scope import ModelActivationScope
from omnibase_core.models.scope.model_applicability_scope import ModelApplicabilityScope
from omnibase_core.models.scope.model_artifact_enforcement import (
    ModelArtifactEnforcement,
)
from omnibase_core.models.scope.model_enforcement_scope import ModelEnforcementScope
from omnibase_core.models.scope.model_integration_filter import ModelIntegrationFilter
from omnibase_core.models.scope.model_repo_filter import ModelRepoFilter
from omnibase_core.models.scope.model_scope_predicate import ModelScopePredicate
from omnibase_core.models.scope.model_state_filter import ModelStateFilter
from omnibase_core.models.scope.model_ticket_filter import ModelTicketFilter
from omnibase_core.models.scope.model_unavailable_behavior import (
    ModelUnavailableBehavior,
)

__all__ = [
    "ModelActivationScope",
    "ModelApplicabilityScope",
    "ModelArtifactEnforcement",
    "ModelEnforcementScope",
    "ModelIntegrationFilter",
    "ModelRepoFilter",
    "ModelScopePredicate",
    "ModelStateFilter",
    "ModelTicketFilter",
    "ModelUnavailableBehavior",
]
