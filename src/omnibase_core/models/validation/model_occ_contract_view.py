# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A ticket's OCC contract read across the legacy and per-PR layouts (OMN-20068)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_occ_contract_source import (
    ModelOccContractSource,
)


class ModelOccContractView(BaseModel):
    """The union of a ticket's legacy contract file and its per-PR files.

    ``data`` is the contract the readers iterate: the legacy file's parsed
    content unchanged when it is the only source, otherwise the legacy mapping
    (or ``{"ticket_id": ...}``) with ``dod_evidence`` holding every source's
    items. ``entry_sources`` maps each ``dod_evidence`` id to the file that
    declares it, which is the file its receipts bind to.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticket_id: str
    sources: tuple[ModelOccContractSource, ...]
    data: object
    entry_sources: dict[str, ModelOccContractSource]

    @property
    def legacy(self) -> ModelOccContractSource | None:
        return next((s for s in self.sources if s.is_legacy), None)

    @property
    def primary(self) -> ModelOccContractSource:
        """The legacy file when present, else the first per-PR file by name."""
        return self.legacy or self.sources[0]

    @property
    def source_hashes(self) -> frozenset[str]:
        return frozenset(s.sha256 for s in self.sources)

    def source_for(self, evidence_item_id: str) -> ModelOccContractSource:
        """The file holding ``evidence_item_id``, else :attr:`primary`.

        An id declared nowhere (a structural self-bind, or an entry that no
        longer exists) resolves to the primary file, which is what the
        single-file read used for it.
        """
        return self.entry_sources.get(evidence_item_id, self.primary)
