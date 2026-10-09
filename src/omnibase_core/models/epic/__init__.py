# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.epic.model_epic_state import (
        EpicState,
        ModelEpicState,
    )
    from omnibase_core.models.epic.model_epic_ticket_status import ModelEpicTicketStatus
    from omnibase_core.models.epic.model_epic_wave import ModelEpicWave

__all__ = [
    "EpicState",
    "ModelEpicState",
    "ModelEpicTicketStatus",
    "ModelEpicWave",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EpicState": ("omnibase_core.models.epic.model_epic_state", "EpicState"),
    "ModelEpicState": ("omnibase_core.models.epic.model_epic_state", "ModelEpicState"),
    "ModelEpicTicketStatus": (
        "omnibase_core.models.epic.model_epic_ticket_status",
        "ModelEpicTicketStatus",
    ),
    "ModelEpicWave": ("omnibase_core.models.epic.model_epic_wave", "ModelEpicWave"),
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
