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

from omnibase_core.runtime.mixin_node_dispatch import MixinNodeDispatch
from omnibase_core.runtime.runtime_file_registry import FileRegistry
from omnibase_core.runtime.runtime_local import (
    ResolvedRoutingEntry,
    RuntimeLocal,
    load_workflow_contract,
    parse_backend_overrides,
)
from omnibase_core.runtime.runtime_local_adapter import LocalRuntimeBusAdapter

__all__ = [
    "FileRegistry",
    "LocalRuntimeBusAdapter",
    "MixinNodeDispatch",
    "ResolvedRoutingEntry",
    "RuntimeLocal",
    "load_workflow_contract",
    "parse_backend_overrides",
]
