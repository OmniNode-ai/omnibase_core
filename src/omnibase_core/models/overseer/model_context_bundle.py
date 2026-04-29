# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextBundle union type alias for routing engine dispatch (OMN-10251).

Re-exports all context bundle level classes and provides the union type alias.
"""

from __future__ import annotations

from omnibase_core.models.overseer.model_context_bundle_base import _ContextBundleBase
from omnibase_core.models.overseer.model_context_bundle_l0 import ModelContextBundleL0
from omnibase_core.models.overseer.model_context_bundle_l1 import ModelContextBundleL1
from omnibase_core.models.overseer.model_context_bundle_l2 import ModelContextBundleL2
from omnibase_core.models.overseer.model_context_bundle_l3 import ModelContextBundleL3
from omnibase_core.models.overseer.model_context_bundle_l4 import ModelContextBundleL4

ModelContextBundle = (
    ModelContextBundleL0
    | ModelContextBundleL1
    | ModelContextBundleL2
    | ModelContextBundleL3
    | ModelContextBundleL4
)
"""Union type alias for routing engine dispatch."""

__all__ = [
    "_ContextBundleBase",
    "ModelContextBundle",
    "ModelContextBundleL0",
    "ModelContextBundleL1",
    "ModelContextBundleL2",
    "ModelContextBundleL3",
    "ModelContextBundleL4",
]
