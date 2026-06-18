# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ContractGraphContractRef — a stable, hashed reference to one source contract.

Phase 2 Contract Graph IR (OMN-13132, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2).

DISTINCT from the validation-event ``ModelContractRef``
(``models/events/contract_validation/model_contract_ref.py``) and from the
workflow-viz graph models (``models/graph/``). This reference records *which*
source contract an IR node was imported from, the dialect adapter that imported
it, and the stable sha256 over the canonicalized contract bytes so diff evidence
cannot drift between runs.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelContractGraphContractRef"]


class ModelContractGraphContractRef(BaseModel):
    """A hashed reference to one imported source contract.

    ``source_contract_sha256`` is the sha256 (``"sha256:<hex>"``) over the
    canonicalized contract bytes; ``adapter_version_sha256`` is the stable hash
    of the adapter that imported it. Together they pin the exact source + import
    logic that produced an IR node so two runs over the same inputs yield
    byte-identical references.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ref_id: str = Field(  # string-id-ok: semantic ref label, not a UUID
        ...,
        description="Stable semantic identifier for this contract reference",
        min_length=1,
    )
    source_path: str = Field(
        ...,
        description="Repo-relative path of the source contract this ref imports",
        min_length=1,
    )
    dialect: str = Field(
        ...,
        description="Dialect adapter name that imported this contract (e.g. 'node', 'ui_component')",
        min_length=1,
    )
    source_contract_sha256: str = Field(
        ...,
        description="sha256:<hex> over the canonicalized source contract bytes",
        min_length=8,
    )
    adapter_version_sha256: str = Field(
        ...,
        description="sha256:<hex> stable version hash of the importing adapter",
        min_length=8,
    )
