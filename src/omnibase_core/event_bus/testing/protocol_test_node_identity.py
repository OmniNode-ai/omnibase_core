# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Structural duck type for the ``node_identity`` argument in shared contract tests.

Split into its own module (from ``contract_event_bus_substrate.py``) to
satisfy the single-class-per-file convention.

.. versionadded:: OMN-15789
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolTestNodeIdentity(Protocol):
    """Structural duck type for the ``node_identity`` argument.

    Defined locally (not imported from ``omnibase_core.protocols``): the
    OMN-14340 import-layering ratchet hard-fails any NEW core module
    importing into the ``protocols`` hub.
    """

    env: str
    service: str
    node_name: str
    version: str


__all__: list[str] = ["ProtocolTestNodeIdentity"]
