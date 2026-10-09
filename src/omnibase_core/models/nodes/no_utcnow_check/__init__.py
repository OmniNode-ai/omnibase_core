# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""no_utcnow_check COMPUTE node models (OMN-14656).

The report/finding shapes are NOT node-local — this node returns the
canonical OMN-2362 generic validator report
(:mod:`omnibase_core.models.validation.model_validation_report`), not a
per-node fork. Import ``ModelValidationReport`` /
``ModelValidationFindingEmbed`` from there.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.nodes.no_utcnow_check.model_no_utcnow_check_input import (
        ModelNoUtcnowCheckInput,
    )
    from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
        ModelSourceFile,
    )

__all__ = [
    "ModelNoUtcnowCheckInput",
    "ModelSourceFile",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelNoUtcnowCheckInput": (
        "omnibase_core.models.nodes.no_utcnow_check.model_no_utcnow_check_input",
        "ModelNoUtcnowCheckInput",
    ),
    "ModelSourceFile": (
        "omnibase_core.models.nodes.no_utcnow_check.model_source_file",
        "ModelSourceFile",
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
