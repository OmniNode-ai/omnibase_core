# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""test_selector COMPUTE node package (OMN-14700).

Exposes :class:`NodeTestSelectorCompute` — the RSD-regenerated canonical form of
the governed impacted-test selector (``scripts/ci/detect_test_paths.py``). Pure,
deterministic, def-B ``handle(request) -> response``; emits the existing
``ModelTestSelection`` shape.
"""

from omnibase_core.nodes.node_test_selector_compute.handler import (
    NodeTestSelectorCompute,
)

__all__ = ["NodeTestSelectorCompute"]
