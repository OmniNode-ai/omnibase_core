# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextSourceRequest — one read against a context source (OMN-18531 / TC.1)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_context_factor import EnumContextFactor
from omnibase_core.models.context.model_context_access import ModelContextAccess
from omnibase_core.models.context.model_context_caller_scope import (
    ModelContextCallerScope,
)

__all__ = ["ModelContextSourceRequest"]


class ModelContextSourceRequest(BaseModel):
    """What a source is asked for, on whose behalf, and at which revision.

    ``access`` has no default: a request without it is refused at
    construction. ``caller_scope`` is the pack request's typed scope passed
    through unchanged.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    factor: EnumContextFactor
    scopes: tuple[str, ...] = ()
    task_kind: str | None = None
    caller_scope: ModelContextCallerScope = Field(
        default_factory=ModelContextCallerScope
    )
    access: ModelContextAccess
    revision: str = Field(
        min_length=1,
        description="Commit, ledger watermark or captured watermark to read at",
    )
