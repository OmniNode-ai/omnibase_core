# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed contract surface for deterministic execution graph replay."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.execution_graph_replay.model_execution_graph_anchor import (
        ModelExecutionGraphAnchor,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_annotations import (
        ModelExecutionGraphAnnotations,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_edge import (
        ModelExecutionGraphEdge,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_endpoint import (
        ModelExecutionGraphEndpoint,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_label import (
        ModelExecutionGraphLabel,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_node import (
        ModelExecutionGraphNode,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_replay import (
        ModelExecutionGraphReplay,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_replay_policy import (
        ModelExecutionGraphReplayPolicy,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_replay_view import (
        ModelExecutionGraph,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_request import (
        ModelExecutionGraphRequest,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_source_cursor import (
        ModelExecutionGraphSourceCursor,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_source_ref import (
        ModelExecutionGraphSourceRef,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_stored_chain_annotation import (
        ModelExecutionGraphStoredChainAnnotation,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_stored_verdict_annotation import (
        ModelExecutionGraphStoredVerdictAnnotation,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_terminal_refusal import (
        ModelExecutionGraphTerminalRefusal,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_terminal_result import (
        ModelExecutionGraphTerminalResult,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_topology_version import (
        ModelExecutionGraphTopologyVersion,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_unresolved import (
        ModelExecutionGraphUnresolved,
    )
    from omnibase_core.models.execution_graph_replay.model_execution_graph_verdict import (
        ModelExecutionGraphVerdict,
    )

__all__ = [
    "ModelExecutionGraph",
    "ModelExecutionGraphAnchor",
    "ModelExecutionGraphAnnotations",
    "ModelExecutionGraphEdge",
    "ModelExecutionGraphEndpoint",
    "ModelExecutionGraphLabel",
    "ModelExecutionGraphNode",
    "ModelExecutionGraphReplay",
    "ModelExecutionGraphReplayPolicy",
    "ModelExecutionGraphRequest",
    "ModelExecutionGraphSourceCursor",
    "ModelExecutionGraphSourceRef",
    "ModelExecutionGraphStoredChainAnnotation",
    "ModelExecutionGraphStoredVerdictAnnotation",
    "ModelExecutionGraphTopologyVersion",
    "ModelExecutionGraphTerminalRefusal",
    "ModelExecutionGraphTerminalResult",
    "ModelExecutionGraphUnresolved",
    "ModelExecutionGraphVerdict",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelExecutionGraphAnchor": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_anchor",
        "ModelExecutionGraphAnchor",
    ),
    "ModelExecutionGraphAnnotations": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_annotations",
        "ModelExecutionGraphAnnotations",
    ),
    "ModelExecutionGraphEdge": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_edge",
        "ModelExecutionGraphEdge",
    ),
    "ModelExecutionGraphEndpoint": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_endpoint",
        "ModelExecutionGraphEndpoint",
    ),
    "ModelExecutionGraphLabel": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_label",
        "ModelExecutionGraphLabel",
    ),
    "ModelExecutionGraphNode": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_node",
        "ModelExecutionGraphNode",
    ),
    "ModelExecutionGraphReplay": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_replay",
        "ModelExecutionGraphReplay",
    ),
    "ModelExecutionGraphReplayPolicy": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_replay_policy",
        "ModelExecutionGraphReplayPolicy",
    ),
    "ModelExecutionGraph": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_replay_view",
        "ModelExecutionGraph",
    ),
    "ModelExecutionGraphRequest": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_request",
        "ModelExecutionGraphRequest",
    ),
    "ModelExecutionGraphSourceCursor": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_source_cursor",
        "ModelExecutionGraphSourceCursor",
    ),
    "ModelExecutionGraphSourceRef": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_source_ref",
        "ModelExecutionGraphSourceRef",
    ),
    "ModelExecutionGraphStoredChainAnnotation": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_stored_chain_annotation",
        "ModelExecutionGraphStoredChainAnnotation",
    ),
    "ModelExecutionGraphStoredVerdictAnnotation": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_stored_verdict_annotation",
        "ModelExecutionGraphStoredVerdictAnnotation",
    ),
    "ModelExecutionGraphTerminalRefusal": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_terminal_refusal",
        "ModelExecutionGraphTerminalRefusal",
    ),
    "ModelExecutionGraphTerminalResult": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_terminal_result",
        "ModelExecutionGraphTerminalResult",
    ),
    "ModelExecutionGraphTopologyVersion": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_topology_version",
        "ModelExecutionGraphTopologyVersion",
    ),
    "ModelExecutionGraphUnresolved": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_unresolved",
        "ModelExecutionGraphUnresolved",
    ),
    "ModelExecutionGraphVerdict": (
        "omnibase_core.models.execution_graph_replay.model_execution_graph_verdict",
        "ModelExecutionGraphVerdict",
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
