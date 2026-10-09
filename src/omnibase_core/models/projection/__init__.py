# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Projection Models - Bases for read-optimized state projections.

Provides abstract base classes and concrete models for projection management
in CQRS architectures with eventual consistency.

Version: 1.0.0
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_degraded_behavior import EnumDegradedBehavior

    from .model_cursor_contract import ModelCursorContract
    from .model_projection_base import ModelProjectionBase
    from .model_projection_contract import ModelProjectionContract
    from .model_upsert_plan import (
        ALLOWED_WRITE_ATTESTATION_SQL,
        SQL_EXPRESSION_SENTINEL_PREFIX,
        WRITE_ATTESTATION_COLUMNS,
        ModelUpsertPlan,
        build_upsert_plan,
    )
    from .model_watermark import ModelProjectionWatermark

__all__ = [
    "ALLOWED_WRITE_ATTESTATION_SQL",
    "SQL_EXPRESSION_SENTINEL_PREFIX",
    "WRITE_ATTESTATION_COLUMNS",
    "EnumDegradedBehavior",
    "ModelCursorContract",
    "ModelProjectionBase",
    "ModelProjectionContract",
    "ModelProjectionWatermark",
    "ModelUpsertPlan",
    "build_upsert_plan",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumDegradedBehavior": (
        "omnibase_core.enums.enum_degraded_behavior",
        "EnumDegradedBehavior",
    ),
    "ModelCursorContract": (
        "omnibase_core.models.projection.model_cursor_contract",
        "ModelCursorContract",
    ),
    "ModelProjectionBase": (
        "omnibase_core.models.projection.model_projection_base",
        "ModelProjectionBase",
    ),
    "ModelProjectionContract": (
        "omnibase_core.models.projection.model_projection_contract",
        "ModelProjectionContract",
    ),
    "ALLOWED_WRITE_ATTESTATION_SQL": (
        "omnibase_core.models.projection.model_upsert_plan",
        "ALLOWED_WRITE_ATTESTATION_SQL",
    ),
    "SQL_EXPRESSION_SENTINEL_PREFIX": (
        "omnibase_core.models.projection.model_upsert_plan",
        "SQL_EXPRESSION_SENTINEL_PREFIX",
    ),
    "WRITE_ATTESTATION_COLUMNS": (
        "omnibase_core.models.projection.model_upsert_plan",
        "WRITE_ATTESTATION_COLUMNS",
    ),
    "ModelUpsertPlan": (
        "omnibase_core.models.projection.model_upsert_plan",
        "ModelUpsertPlan",
    ),
    "build_upsert_plan": (
        "omnibase_core.models.projection.model_upsert_plan",
        "build_upsert_plan",
    ),
    "ModelProjectionWatermark": (
        "omnibase_core.models.projection.model_watermark",
        "ModelProjectionWatermark",
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
