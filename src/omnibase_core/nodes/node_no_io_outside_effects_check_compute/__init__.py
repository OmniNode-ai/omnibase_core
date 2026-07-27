# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""no_io_outside_effects_check COMPUTE node package (OMN-14694 / OMN-14662).

Exposes :class:`NodeNoIoOutsideEffectsCheckCompute` — keys off each node's
declared archetype (``contract.yaml``) and flags forbidden I/O surfaces
(database, filesystem writes, network, subprocess, git, Linear, and direct
adapter/bus instantiation) inside ``.py`` modules that sit in a **non-EFFECT**
node package, returning a ``ModelValidationReport``.
"""

from omnibase_core.nodes.node_no_io_outside_effects_check_compute.handler import (
    NodeNoIoOutsideEffectsCheckCompute,
)

__all__ = ["NodeNoIoOutsideEffectsCheckCompute"]
