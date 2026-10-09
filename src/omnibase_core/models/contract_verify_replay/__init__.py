# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Models for contract.verify.replay compute node (OMN-2759).

Provides the input/output Pydantic models and sub-models used by
:class:`~omnibase_core.nodes.node_contract_verify_replay_compute.handler.NodeContractVerifyReplayCompute`.

.. versionadded:: 0.20.0
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.contract_verify_replay.model_verify_check_result import (
        ModelVerifyCheckResult,
    )
    from omnibase_core.models.contract_verify_replay.model_verify_options import (
        ModelVerifyOptions,
    )
    from omnibase_core.models.contract_verify_replay.model_verify_replay_input import (
        ModelVerifyReplayInput,
    )
    from omnibase_core.models.contract_verify_replay.model_verify_replay_output import (
        ModelVerifyReplayOutput,
    )

__all__ = [
    "ModelVerifyCheckResult",
    "ModelVerifyOptions",
    "ModelVerifyReplayInput",
    "ModelVerifyReplayOutput",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelVerifyCheckResult": (
        "omnibase_core.models.contract_verify_replay.model_verify_check_result",
        "ModelVerifyCheckResult",
    ),
    "ModelVerifyOptions": (
        "omnibase_core.models.contract_verify_replay.model_verify_options",
        "ModelVerifyOptions",
    ),
    "ModelVerifyReplayInput": (
        "omnibase_core.models.contract_verify_replay.model_verify_replay_input",
        "ModelVerifyReplayInput",
    ),
    "ModelVerifyReplayOutput": (
        "omnibase_core.models.contract_verify_replay.model_verify_replay_output",
        "ModelVerifyReplayOutput",
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
