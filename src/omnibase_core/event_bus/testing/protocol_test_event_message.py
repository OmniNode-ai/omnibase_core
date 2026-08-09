# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Structural duck type for the message a shared contract-test handler receives.

Split into its own module (from ``contract_event_bus_substrate.py``) to
satisfy the single-class-per-file convention.

.. versionadded:: OMN-15789
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolTestEventMessage(Protocol):
    """Structural duck type for the message a test handler receives.

    Defined locally (not imported from ``omnibase_core.protocols``): the
    OMN-14340 import-layering ratchet hard-fails any NEW core module
    importing into the ``protocols`` hub. Only the fields these contract
    tests actually read (``topic``, ``key``, ``value``) are declared --
    narrower than the real ``ProtocolEventMessage`` (which also requires
    ``headers``/``ack``/``nack``), which is fine: every concrete
    ``ModelEventMessage`` the substrates deliver satisfies this narrower
    shape too.
    """

    @property
    def topic(self) -> str: ...

    @property
    def key(self) -> bytes | None: ...

    @property
    def value(self) -> bytes: ...


__all__: list[str] = ["ProtocolTestEventMessage"]
