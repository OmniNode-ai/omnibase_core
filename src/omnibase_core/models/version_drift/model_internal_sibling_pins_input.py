# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the internal sibling pin check (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.version_drift.model_internal_sibling_pins_contract import (
    ModelInternalSiblingPinsContract,
)
from omnibase_core.models.version_drift.model_sibling_dev_tags import (
    ModelSiblingDevTags,
)

__all__ = ["ModelInternalSiblingPinsInput"]


class ModelInternalSiblingPinsInput(BaseModel):
    """The pyproject files of one consumer and the contract they are judged by.

    Attributes:
        files: Repository-relative (path, source) pairs of pyproject.toml files.
        contract: The internal siblings and the dev merge tag form.
        dev_tags: Sibling tag inventories; None skips staleness for offline use.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: tuple[ModelSourceFile, ...] = Field(default=())
    contract: ModelInternalSiblingPinsContract
    dev_tags: tuple[ModelSiblingDevTags, ...] | None = None
