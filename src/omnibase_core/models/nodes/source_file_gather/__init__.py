# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""source_file_gather EFFECT node models (OMN-14656)."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.nodes.source_file_gather.model_gathered_source_file import (
        ModelGatheredSourceFile,
    )
    from omnibase_core.models.nodes.source_file_gather.model_skipped_source_file import (
        ModelSkippedSourceFile,
    )
    from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
        ModelSourceFileGatherInput,
    )
    from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_output import (
        ModelSourceFileGatherOutput,
    )

__all__ = [
    "ModelGatheredSourceFile",
    "ModelSkippedSourceFile",
    "ModelSourceFileGatherInput",
    "ModelSourceFileGatherOutput",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelGatheredSourceFile": (
        "omnibase_core.models.nodes.source_file_gather.model_gathered_source_file",
        "ModelGatheredSourceFile",
    ),
    "ModelSkippedSourceFile": (
        "omnibase_core.models.nodes.source_file_gather.model_skipped_source_file",
        "ModelSkippedSourceFile",
    ),
    "ModelSourceFileGatherInput": (
        "omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input",
        "ModelSourceFileGatherInput",
    ),
    "ModelSourceFileGatherOutput": (
        "omnibase_core.models.nodes.source_file_gather.model_source_file_gather_output",
        "ModelSourceFileGatherOutput",
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
