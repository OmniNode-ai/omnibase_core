# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Minimal ProtocolNodeIdentity-compatible identity for the shared
``event_bus_substrate`` contract tests.

Split into its own module (from ``contract_event_bus_substrate.py``) to
satisfy the single-class-per-file convention.

.. versionadded:: OMN-15789
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ContractNodeIdentity:
    """Minimal ProtocolNodeIdentity-compatible identity for contract tests."""

    env: str = "onex-dev"
    service: str = "omnimarket"
    node_name: str = "node_delegation_orchestrator"
    version: str = "v1"


__all__: list[str] = ["ContractNodeIdentity"]
