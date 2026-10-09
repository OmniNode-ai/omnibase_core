# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical I/O models for the test-selector COMPUTE node (OMN-14700).

Promoted verbatim from ``scripts/ci/test_selection_models.py`` and
``scripts/ci/test_selection_loader.py`` into the canonical ``omnibase_core``
model layer (root CLAUDE.md rule #7) so the RSD-regenerated
``node_test_selector_compute`` node and the legacy ``detect_test_paths.py``
oracle share ONE definition of each shape (no fork). The two ``scripts/ci``
modules re-export these names until the CI/pre-push swap follow-up
(OMN-14700 DoD 2/3) deletes the script.

Parent epic: OMN-2362 (Generic Validator Node Architecture / WS8).
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_full_suite_reason import EnumFullSuiteReason
    from omnibase_core.models.nodes.test_selector.model_adjacency_map import (
        ModelAdjacencyEntry,
        ModelAdjacencyMap,
        ModelThresholds,
    )
    from omnibase_core.models.nodes.test_selector.model_test_selection import (
        ModelTestSelection,
        ModuleName,
        TestPath,
    )
    from omnibase_core.models.nodes.test_selector.model_test_selection_request import (
        ModelTestSelectionRequest,
    )

__all__ = [
    "EnumFullSuiteReason",
    "ModelAdjacencyEntry",
    "ModelAdjacencyMap",
    "ModelTestSelection",
    "ModelTestSelectionRequest",
    "ModelThresholds",
    "ModuleName",
    "TestPath",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumFullSuiteReason": (
        "omnibase_core.enums.enum_full_suite_reason",
        "EnumFullSuiteReason",
    ),
    "ModelAdjacencyEntry": (
        "omnibase_core.models.nodes.test_selector.model_adjacency_map",
        "ModelAdjacencyEntry",
    ),
    "ModelAdjacencyMap": (
        "omnibase_core.models.nodes.test_selector.model_adjacency_map",
        "ModelAdjacencyMap",
    ),
    "ModelThresholds": (
        "omnibase_core.models.nodes.test_selector.model_adjacency_map",
        "ModelThresholds",
    ),
    "ModelTestSelection": (
        "omnibase_core.models.nodes.test_selector.model_test_selection",
        "ModelTestSelection",
    ),
    "ModuleName": (
        "omnibase_core.models.nodes.test_selector.model_test_selection",
        "ModuleName",
    ),
    "TestPath": (
        "omnibase_core.models.nodes.test_selector.model_test_selection",
        "TestPath",
    ),
    "ModelTestSelectionRequest": (
        "omnibase_core.models.nodes.test_selector.model_test_selection_request",
        "ModelTestSelectionRequest",
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
