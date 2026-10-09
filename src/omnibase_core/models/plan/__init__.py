# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.plan.model_dod_item import DoDItem, ModelDoDItem
    from omnibase_core.models.plan.model_plan_contract import (
        ModelPlanContract,
        PlanContract,
    )
    from omnibase_core.models.plan.model_plan_document import (
        ModelPlanDocument,
        PlanDocument,
    )
    from omnibase_core.models.plan.model_plan_entry import ModelPlanEntry, PlanEntry
    from omnibase_core.models.plan.model_plan_review_result import (
        ModelPlanReviewResult,
        PlanReviewResult,
    )
    from omnibase_core.models.plan.model_plan_ticket_link import (
        ModelPlanTicketLink,
        PlanTicketLink,
    )

__all__ = [
    "DoDItem",
    "ModelDoDItem",
    "ModelPlanContract",
    "ModelPlanDocument",
    "ModelPlanEntry",
    "ModelPlanReviewResult",
    "ModelPlanTicketLink",
    "PlanContract",
    "PlanDocument",
    "PlanEntry",
    "PlanReviewResult",
    "PlanTicketLink",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "DoDItem": ("omnibase_core.models.plan.model_dod_item", "DoDItem"),
    "ModelDoDItem": ("omnibase_core.models.plan.model_dod_item", "ModelDoDItem"),
    "ModelPlanContract": (
        "omnibase_core.models.plan.model_plan_contract",
        "ModelPlanContract",
    ),
    "PlanContract": ("omnibase_core.models.plan.model_plan_contract", "PlanContract"),
    "ModelPlanDocument": (
        "omnibase_core.models.plan.model_plan_document",
        "ModelPlanDocument",
    ),
    "PlanDocument": ("omnibase_core.models.plan.model_plan_document", "PlanDocument"),
    "ModelPlanEntry": ("omnibase_core.models.plan.model_plan_entry", "ModelPlanEntry"),
    "PlanEntry": ("omnibase_core.models.plan.model_plan_entry", "PlanEntry"),
    "ModelPlanReviewResult": (
        "omnibase_core.models.plan.model_plan_review_result",
        "ModelPlanReviewResult",
    ),
    "PlanReviewResult": (
        "omnibase_core.models.plan.model_plan_review_result",
        "PlanReviewResult",
    ),
    "ModelPlanTicketLink": (
        "omnibase_core.models.plan.model_plan_ticket_link",
        "ModelPlanTicketLink",
    ),
    "PlanTicketLink": (
        "omnibase_core.models.plan.model_plan_ticket_link",
        "PlanTicketLink",
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
