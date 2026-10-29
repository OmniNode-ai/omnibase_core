# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ci-inheritance handler models (OMN-17427).

The handler returns the canonical OMN-2362 generic validator report
(:mod:`omnibase_core.models.validation.model_validation_report`); the per-file
shape is the shared (path, source) DTO
(:class:`~omnibase_core.models.nodes.no_utcnow_check.model_source_file.ModelSourceFile`).
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_baseline import (
        ModelCiInheritanceBaseline,
    )
    from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_check_input import (
        ModelCiInheritanceCheckInput,
    )
    from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_reference_input import (
        ModelCiInheritanceReferenceInput,
    )
    from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_rules import (
        ModelCiInheritanceRules,
    )
    from omnibase_core.models.nodes.ci_inheritance_check.model_ci_org_reference import (
        ModelCiOrgReference,
    )

__all__ = [
    "ModelCiInheritanceBaseline",
    "ModelCiInheritanceCheckInput",
    "ModelCiInheritanceReferenceInput",
    "ModelCiInheritanceRules",
    "ModelCiOrgReference",
]


_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelCiInheritanceBaseline": (
        "omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_baseline",
        "ModelCiInheritanceBaseline",
    ),
    "ModelCiInheritanceCheckInput": (
        "omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_check_input",
        "ModelCiInheritanceCheckInput",
    ),
    "ModelCiInheritanceReferenceInput": (
        "omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_reference_input",
        "ModelCiInheritanceReferenceInput",
    ),
    "ModelCiInheritanceRules": (
        "omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_rules",
        "ModelCiInheritanceRules",
    ),
    "ModelCiOrgReference": (
        "omnibase_core.models.nodes.ci_inheritance_check.model_ci_org_reference",
        "ModelCiOrgReference",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
