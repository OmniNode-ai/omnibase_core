# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract Graph IR models (OMN-13132 — Phase 2, epic OMN-13129).

The canonical read-only intermediate the plan
(docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2)
calls the Contract Graph IR. Heterogeneous source contracts — backend node
contracts and UI component contracts — are imported into one deterministic graph
of nodes + typed edges, with stable hashes pinning provenance.

These models are DISTINCT from the workflow-viz graph models in
``omnibase_core.models.graph`` (``ModelGraphNode``/``ModelGraphEdge``, whose
``node_id`` is a UUID for orchestrator-graph visualization) and from the
validation-event ``ModelContractRef`` in
``omnibase_core.models.events.contract_validation``. The distinct
``contract_graph`` namespace and ``ModelContractGraph*`` names prevent any
identifier collision.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.contract_graph.model_contract_graph_contract_ref import (
        ModelContractGraphContractRef,
    )
    from omnibase_core.models.contract_graph.model_contract_graph_edge import (
        ModelContractGraphEdge,
    )
    from omnibase_core.models.contract_graph.model_contract_graph_ir import (
        ModelContractGraphIr,
    )
    from omnibase_core.models.contract_graph.model_contract_graph_node import (
        ModelContractGraphNode,
    )
    from omnibase_core.models.contract_graph.model_contract_graph_protocol import (
        ModelContractGraphProtocol,
    )
    from omnibase_core.models.contract_graph.model_contract_graph_source_set import (
        ModelContractGraphSourceSet,
    )

__all__: tuple[str, ...] = (
    "ModelContractGraphIr",
    "ModelContractGraphNode",
    "ModelContractGraphEdge",
    "ModelContractGraphProtocol",
    "ModelContractGraphContractRef",
    "ModelContractGraphSourceSet",
)


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelContractGraphContractRef": (
        "omnibase_core.models.contract_graph.model_contract_graph_contract_ref",
        "ModelContractGraphContractRef",
    ),
    "ModelContractGraphEdge": (
        "omnibase_core.models.contract_graph.model_contract_graph_edge",
        "ModelContractGraphEdge",
    ),
    "ModelContractGraphIr": (
        "omnibase_core.models.contract_graph.model_contract_graph_ir",
        "ModelContractGraphIr",
    ),
    "ModelContractGraphNode": (
        "omnibase_core.models.contract_graph.model_contract_graph_node",
        "ModelContractGraphNode",
    ),
    "ModelContractGraphProtocol": (
        "omnibase_core.models.contract_graph.model_contract_graph_protocol",
        "ModelContractGraphProtocol",
    ),
    "ModelContractGraphSourceSet": (
        "omnibase_core.models.contract_graph.model_contract_graph_source_set",
        "ModelContractGraphSourceSet",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
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
