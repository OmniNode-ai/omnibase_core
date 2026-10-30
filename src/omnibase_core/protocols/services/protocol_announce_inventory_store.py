# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Inventory store protocol of the node announcement step (OMN-21589)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolAnnounceInventoryStore(Protocol):
    """Keeps an announcer's previous inventory across restarts, as JSON text.

    Every name in the previous inventory that is absent from the new one is
    announced as a withdrawal, so a replacement process whose image lost a package
    withdraws that package's contracts with no in-memory event from the old process.
    The payload is ``ModelAnnounceInventory`` serialised to JSON, so a store binds to
    a file, a table or a topic without importing the model.
    """

    async def load(self, announcer_id: str) -> str | None:
        """Return the JSON saved for this announcer, or ``None`` on a first boot."""
        ...

    async def save(self, announcer_id: str, inventory_json: str) -> None:
        """Persist the inventory JSON this announcer just published."""
        ...
