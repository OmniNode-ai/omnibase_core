# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Base for the sections of a view document (OMN-21997).

A section fixes its envelope: the kind it declares, the kind of its envelope's
component, the kind of its envelope's config and the type of its rows all name
the same view kind, and a section that disagrees fails the model. The same rule
reaches the published JSON Schema: each concrete section pins its envelope's
``component_kind`` and ``config_kind`` to its own kind (see
``_pin_envelope_kind``), and its row type is its kind's row model, so a
cross-kind section is refused by a schema validator as well as by Pydantic.

The body is rows or a typed empty state, never both and never neither.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticUndefined

from omnibase_core.models.dashboard.model_view_empty_state import ModelViewEmptyState
from omnibase_core.models.dashboard.model_view_row_base import ModelViewRowBase
from omnibase_core.models.dashboard.model_view_slug import ViewSlug
from omnibase_core.models.dashboard.model_widget_envelope import ModelWidgetEnvelope

if TYPE_CHECKING:
    from pydantic.config import JsonDict

__all__ = ["ModelViewSectionBase"]


def _pin_envelope_kind(schema: JsonDict, model: type[BaseModel]) -> None:
    """Pin the section's envelope to its own kind in the emitted JSON Schema.

    Pydantic cannot express "this field's nested discriminated value must carry
    the discriminator of the enclosing model", so the constraint is added to the
    schema by hand: the envelope must also satisfy a schema that fixes
    ``component.component_kind`` and ``config.config_kind`` to the section's kind.
    """
    kind = model.model_fields["kind"].default
    properties = schema.get("properties")
    if kind is PydanticUndefined or not isinstance(properties, dict):
        return
    pinned: JsonDict = {
        "properties": {
            "component": {"properties": {"component_kind": {"const": kind}}},
            "config": {"properties": {"config_kind": {"const": kind}}},
        }
    }
    properties["envelope"] = {"allOf": [properties["envelope"], pinned]}


class ModelViewSectionBase(BaseModel):
    """A section: one sealed envelope and a body of rows or a typed empty state."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        json_schema_extra=_pin_envelope_kind,
    )

    kind: str = Field(
        ..., description="View kind of this section; the document union discriminator"
    )
    section_id: ViewSlug = Field(
        ..., description="Slug of this section, unique within its document"
    )
    envelope: ModelWidgetEnvelope = Field(
        ...,
        description=(
            "Sealed widget envelope for this section; its component kind and "
            "config kind must equal this section's kind"
        ),
    )
    rows: tuple[ModelViewRowBase, ...] = Field(
        default=(), description="Rows of this section; empty when empty_state is set"
    )
    empty_state: ModelViewEmptyState | None = Field(
        default=None, description="Typed reason there are no rows; None when rows exist"
    )

    @model_validator(mode="after")
    def validate_body_is_rows_xor_empty_state(self) -> Self:
        """Require exactly one of rows or an empty state.

        Raises:
            ValueError: If both are present, or neither is.
        """
        if bool(self.rows) == (self.empty_state is not None):
            raise ValueError(
                f"section '{self.section_id}' must carry rows or an empty_state, "
                f"never both and never neither"
            )
        return self

    @model_validator(mode="after")
    def validate_envelope_matches_kind(self) -> Self:
        """Fail closed when the envelope is for another kind.

        Raises:
            ValueError: If the envelope's component kind or config kind is not
                this section's kind.
        """
        component_kind = self.envelope.component.component_kind.value
        config_kind = self.envelope.config.config_kind
        if component_kind != self.kind or config_kind != self.kind:
            raise ValueError(
                f"section '{self.section_id}' is kind '{self.kind}' but its "
                f"envelope is component_kind '{component_kind}' with config_kind "
                f"'{config_kind}'"
            )
        return self

    @model_validator(mode="after")
    def validate_rows_belong_to_this_section(self) -> Self:
        """Require each row id to name this section, once.

        Raises:
            ValueError: If a row names another section, or two rows share an id.
        """
        seen: set[str] = set()
        for row in self.rows:
            if row.row_id.section_id != self.section_id:
                raise ValueError(
                    f"row {row.row_id.as_string()} names section_id "
                    f"'{row.row_id.section_id}' but sits in section "
                    f"'{self.section_id}'"
                )
            rendered = row.row_id.as_string()
            if rendered in seen:
                raise ValueError(
                    f"duplicate row id {rendered} in section '{self.section_id}'"
                )
            seen.add(rendered)
        return self
