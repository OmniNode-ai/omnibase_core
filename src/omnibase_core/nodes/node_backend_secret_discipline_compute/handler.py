# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeBackendSecretDisciplineCompute — thin node shell.

The handler logic lives in
``omnibase_core.validation.validator_backend_secret_discipline`` and is
importable directly as ``NodeBackendSecretDisciplineCompute``.  This module
re-exports it under the node package for contract-router registration.

ONEX node type: COMPUTE
"""

from __future__ import annotations

from omnibase_core.validation.validator_backend_secret_discipline import (
    HandlerBackendSecretDisciplineCompute,
)

# Re-export the canonical handler class under the node-package alias.
NodeBackendSecretDisciplineCompute = HandlerBackendSecretDisciplineCompute

__all__ = [
    "HandlerBackendSecretDisciplineCompute",
    "NodeBackendSecretDisciplineCompute",
]
