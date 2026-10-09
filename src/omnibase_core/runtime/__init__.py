# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ONEX Runtime Module.

Runtime infrastructure for ONEX node execution,
including contract file loading and the local runtime orchestrator.

Components:
    - FileRegistry: Loads YAML contract files with fail-fast validation
    - RuntimeLocal: Local runtime orchestrator for contract-declared workflows
    - LocalRuntimeBusAdapter: Bridges ONEX handlers to the in-memory event bus

Related:
    - OMN-229: FileRegistry for contract file loading
    - OMN-13444: RuntimeLocal relocated from omnibase_infra (local-first re-convergence)
    - OMN-12549: MixinNodeDispatch node-owned dispatch-selection seam (epic OMN-12525)
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.runtime.mixin_node_dispatch import MixinNodeDispatch
    from omnibase_core.runtime.runtime_dispatch import DispatchRoute, RuntimeDispatch
    from omnibase_core.runtime.runtime_envelope_router import (
        decode_inbound_envelope,
        derive_event_type_from_topic,
        wrap_outbound_envelope,
    )
    from omnibase_core.runtime.runtime_file_registry import FileRegistry
    from omnibase_core.runtime.runtime_local import (
        ResolvedRoutingEntry,
        RuntimeLocal,
        load_workflow_contract,
        parse_backend_overrides,
    )
    from omnibase_core.runtime.runtime_local_adapter import LocalRuntimeBusAdapter

__all__ = [
    "DispatchRoute",
    "FileRegistry",
    "LocalRuntimeBusAdapter",
    "MixinNodeDispatch",
    "ResolvedRoutingEntry",
    "RuntimeDispatch",
    "RuntimeLocal",
    "decode_inbound_envelope",
    "derive_event_type_from_topic",
    "load_workflow_contract",
    "parse_backend_overrides",
    "wrap_outbound_envelope",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "MixinNodeDispatch": (
        "omnibase_core.runtime.mixin_node_dispatch",
        "MixinNodeDispatch",
    ),
    "DispatchRoute": ("omnibase_core.runtime.runtime_dispatch", "DispatchRoute"),
    "RuntimeDispatch": ("omnibase_core.runtime.runtime_dispatch", "RuntimeDispatch"),
    "decode_inbound_envelope": (
        "omnibase_core.runtime.runtime_envelope_router",
        "decode_inbound_envelope",
    ),
    "derive_event_type_from_topic": (
        "omnibase_core.runtime.runtime_envelope_router",
        "derive_event_type_from_topic",
    ),
    "wrap_outbound_envelope": (
        "omnibase_core.runtime.runtime_envelope_router",
        "wrap_outbound_envelope",
    ),
    "FileRegistry": ("omnibase_core.runtime.runtime_file_registry", "FileRegistry"),
    "ResolvedRoutingEntry": (
        "omnibase_core.runtime.runtime_local",
        "ResolvedRoutingEntry",
    ),
    "RuntimeLocal": ("omnibase_core.runtime.runtime_local", "RuntimeLocal"),
    "load_workflow_contract": (
        "omnibase_core.runtime.runtime_local",
        "load_workflow_contract",
    ),
    "parse_backend_overrides": (
        "omnibase_core.runtime.runtime_local",
        "parse_backend_overrides",
    ),
    "LocalRuntimeBusAdapter": (
        "omnibase_core.runtime.runtime_local_adapter",
        "LocalRuntimeBusAdapter",
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
