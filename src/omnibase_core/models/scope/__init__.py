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

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.scope.model_activation_scope import ModelActivationScope
    from omnibase_core.models.scope.model_applicability_scope import (
        ModelApplicabilityScope,
    )
    from omnibase_core.models.scope.model_artifact_enforcement import (
        ModelArtifactEnforcement,
    )
    from omnibase_core.models.scope.model_enforcement_scope import ModelEnforcementScope
    from omnibase_core.models.scope.model_integration_filter import (
        ModelIntegrationFilter,
    )
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelActivationScope": (
        "omnibase_core.models.scope.model_activation_scope",
        "ModelActivationScope",
    ),
    "ModelApplicabilityScope": (
        "omnibase_core.models.scope.model_applicability_scope",
        "ModelApplicabilityScope",
    ),
    "ModelArtifactEnforcement": (
        "omnibase_core.models.scope.model_artifact_enforcement",
        "ModelArtifactEnforcement",
    ),
    "ModelEnforcementScope": (
        "omnibase_core.models.scope.model_enforcement_scope",
        "ModelEnforcementScope",
    ),
    "ModelIntegrationFilter": (
        "omnibase_core.models.scope.model_integration_filter",
        "ModelIntegrationFilter",
    ),
    "ModelRepoFilter": (
        "omnibase_core.models.scope.model_repo_filter",
        "ModelRepoFilter",
    ),
    "ModelScopePredicate": (
        "omnibase_core.models.scope.model_scope_predicate",
        "ModelScopePredicate",
    ),
    "ModelStateFilter": (
        "omnibase_core.models.scope.model_state_filter",
        "ModelStateFilter",
    ),
    "ModelTicketFilter": (
        "omnibase_core.models.scope.model_ticket_filter",
        "ModelTicketFilter",
    ),
    "ModelUnavailableBehavior": (
        "omnibase_core.models.scope.model_unavailable_behavior",
        "ModelUnavailableBehavior",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
