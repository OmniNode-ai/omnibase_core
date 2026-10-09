# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""validation_report_write EFFECT node models (OMN-20565)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
        ModelValidationReportWriteInput,
    )
    from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_output import (
        ModelValidationReportWriteOutput,
    )

__all__ = ["ModelValidationReportWriteInput", "ModelValidationReportWriteOutput"]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelValidationReportWriteInput": (
        "omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input",
        "ModelValidationReportWriteInput",
    ),
    "ModelValidationReportWriteOutput": (
        "omnibase_core.models.nodes.validation_report_write.model_validation_report_write_output",
        "ModelValidationReportWriteOutput",
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
