# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One method of a handler class, as facts for the handler-shape check (OMN-21536)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelHandlerShapeMethod"]


class ModelHandlerShapeMethod(BaseModel):
    """The signature and self-mutation facts of a method; no source text."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str
    line: int
    positional_names: tuple[str, ...] = Field(
        default=(), description="Positional parameters after the implicit receiver."
    )
    positional_annotations: tuple[str, ...] = Field(
        default=(), description="Annotation text per positional parameter, '' if none."
    )
    has_kwargs: bool = False
    assigns_self_attribute: bool = Field(
        default=False, description="The body assigns to an attribute of the receiver."
    )
    self_attribute_calls: tuple[str, ...] = Field(
        default=(), description="Method names called on an attribute of the receiver."
    )
