# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Models of the work-ledger fold COMPUTE node (OMN-19405, typed work ledger T4).

``ModelWorkLedgerFoldInput`` is the node's input and ``ModelWorkLedgerState``
its output. ``ModelWorkLedgerVerdict`` and ``ModelWorkLedgerHealth`` are what
the pure queries over that state return.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.nodes.work_ledger_state.model_hold_in_force import (
        ModelHoldInForce,
    )
    from omnibase_core.models.nodes.work_ledger_state.model_invalid_question_ref import (
        ModelInvalidQuestionRef,
    )
    from omnibase_core.models.nodes.work_ledger_state.model_invalid_release import (
        ModelInvalidRelease,
    )
    from omnibase_core.models.nodes.work_ledger_state.model_question_state import (
        ModelQuestionState,
    )
    from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_fold_input import (
        ModelWorkLedgerFoldInput,
    )
    from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_health import (
        ModelWorkLedgerHealth,
    )
    from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_projection_row import (
        ModelWorkLedgerProjectionRow,
    )
    from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_projection_snapshot import (
        ModelWorkLedgerProjectionSnapshot,
    )
    from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_state import (
        ModelWorkLedgerState,
    )
    from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_verdict import (
        ModelWorkLedgerVerdict,
    )

__all__ = [
    "ModelHoldInForce",
    "ModelInvalidQuestionRef",
    "ModelInvalidRelease",
    "ModelWorkLedgerProjectionRow",
    "ModelWorkLedgerProjectionSnapshot",
    "ModelQuestionState",
    "ModelWorkLedgerFoldInput",
    "ModelWorkLedgerHealth",
    "ModelWorkLedgerState",
    "ModelWorkLedgerVerdict",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelHoldInForce": (
        "omnibase_core.models.nodes.work_ledger_state.model_hold_in_force",
        "ModelHoldInForce",
    ),
    "ModelInvalidQuestionRef": (
        "omnibase_core.models.nodes.work_ledger_state.model_invalid_question_ref",
        "ModelInvalidQuestionRef",
    ),
    "ModelInvalidRelease": (
        "omnibase_core.models.nodes.work_ledger_state.model_invalid_release",
        "ModelInvalidRelease",
    ),
    "ModelQuestionState": (
        "omnibase_core.models.nodes.work_ledger_state.model_question_state",
        "ModelQuestionState",
    ),
    "ModelWorkLedgerFoldInput": (
        "omnibase_core.models.nodes.work_ledger_state.model_work_ledger_fold_input",
        "ModelWorkLedgerFoldInput",
    ),
    "ModelWorkLedgerHealth": (
        "omnibase_core.models.nodes.work_ledger_state.model_work_ledger_health",
        "ModelWorkLedgerHealth",
    ),
    "ModelWorkLedgerProjectionRow": (
        "omnibase_core.models.nodes.work_ledger_state.model_work_ledger_projection_row",
        "ModelWorkLedgerProjectionRow",
    ),
    "ModelWorkLedgerProjectionSnapshot": (
        "omnibase_core.models.nodes.work_ledger_state.model_work_ledger_projection_snapshot",
        "ModelWorkLedgerProjectionSnapshot",
    ),
    "ModelWorkLedgerState": (
        "omnibase_core.models.nodes.work_ledger_state.model_work_ledger_state",
        "ModelWorkLedgerState",
    ),
    "ModelWorkLedgerVerdict": (
        "omnibase_core.models.nodes.work_ledger_state.model_work_ledger_verdict",
        "ModelWorkLedgerVerdict",
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
