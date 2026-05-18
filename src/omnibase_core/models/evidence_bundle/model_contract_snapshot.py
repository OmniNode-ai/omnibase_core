# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContractSnapshot — point-in-time snapshot of contracts used in a run."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelContractSnapshot(BaseModel):
    """Snapshot of contracts that were active during an evidence bundle run.

    Each entry in ``contracts`` is a dict containing at minimum ``name`` and
    ``hash`` fields, providing an auditable record of which contract versions
    were in effect when the bundle was produced.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: str
    contracts: tuple[dict[str, object], ...]


__all__ = ["ModelContractSnapshot"]
