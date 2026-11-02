# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One row-model field and where its value comes from (OMN-21997)."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dashboard.model_view_column_name import ViewColumnName
from omnibase_core.models.dashboard.model_view_field_source_column import (
    ModelViewFieldSourceColumn,
)
from omnibase_core.models.dashboard.model_view_field_source_constant import (
    ModelViewFieldSourceConstant,
)
from omnibase_core.models.dashboard.model_view_field_source_reference import (
    ModelViewFieldSourceReference,
)

__all__ = ["ModelViewFieldBinding", "ModelViewFieldSource"]

#: A field's source. Columns, constants and references only; there is no
#: expression member, so a formula has nowhere to go.
ModelViewFieldSource = Annotated[
    ModelViewFieldSourceColumn
    | ModelViewFieldSourceConstant
    | ModelViewFieldSourceReference,
    Field(discriminator="source_kind"),
]


class ModelViewFieldBinding(BaseModel):
    """Bind one field of the section's row model to a source."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    target: ViewColumnName = Field(..., description="Field of the row model to fill")
    source: ModelViewFieldSource = Field(..., description="Where the value comes from")
