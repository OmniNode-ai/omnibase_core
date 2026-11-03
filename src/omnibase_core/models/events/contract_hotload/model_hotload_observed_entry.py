# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The latest registry change a runtime has folded for one name (OMN-21226)."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_contract_hotload_reason import EnumContractHotloadReason
from omnibase_core.enums.enum_contract_hotload_status import EnumContractHotloadStatus

__all__ = ["ModelHotloadObservedEntry"]


class ModelHotloadObservedEntry(BaseModel):
    """What the runtime has observed for one name (plan section 3.2).

    It is the highest accepted or removal version the runtime has folded, with the
    status of that record. After a refused replacement it reads version 2,
    ``refused``; after a removal it reads version n, ``removed``.

    Attributes:
        registry_version: The highest version folded.
        status: What the runtime did with that record.
        reason: Typed reason, or ``None``. A ``refused`` entry must carry one.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    registry_version: int = Field(ge=1)
    status: EnumContractHotloadStatus
    reason: EnumContractHotloadReason | None

    @model_validator(mode="after")
    def _a_refusal_names_its_reason(self) -> Self:
        if self.status is EnumContractHotloadStatus.REFUSED and self.reason is None:
            raise ValueError("a refused entry must carry a reason")
        return self
