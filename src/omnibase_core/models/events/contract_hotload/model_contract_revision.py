# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One immutable record per registered contract revision (OMN-21226)."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelContractRevision"]

_REVISION_KEY = re.compile(r"^.+@[0-9a-f]{64}$")


class ModelContractRevision(BaseModel):
    """A contract at one content hash, with its text.

    Attributes:
        entity_id: ``{name}@{content_hash}``, the record's compaction key.
        contract_yaml: The contract, as text.
        registry_version: The registry version that registered this revision.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    entity_id: str = Field(min_length=1)
    contract_yaml: str = Field(min_length=1)
    registry_version: int = Field(ge=1)

    @field_validator("entity_id")
    @classmethod
    def _entity_id_is_name_at_hash(cls, value: str) -> str:
        if _REVISION_KEY.match(value) is None:
            raise ValueError(
                "entity_id must be '{name}@{content_hash}' with a 64-character "
                "lowercase hexadecimal content hash"
            )
        return value
