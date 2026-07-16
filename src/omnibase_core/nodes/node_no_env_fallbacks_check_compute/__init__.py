# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""no_env_fallbacks_check COMPUTE node package (OMN-14659).

Exposes :class:`NodeNoEnvFallbacksCheckCompute` — line-scans explicit (path,
source) pairs for localhost/hardcoded-endpoint fallback defaults in Python
and shell source, and returns a ``ModelValidationReport``.
"""

from omnibase_core.nodes.node_no_env_fallbacks_check_compute.handler import (
    NodeNoEnvFallbacksCheckCompute,
)

__all__ = ["NodeNoEnvFallbacksCheckCompute"]
