# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A concrete adapter of one protocol that a handler must not import or construct."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelConcreteBinding(BaseModel):
    """Module prefixes and class names of one binding, and where it may be used."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    code: str = Field(min_length=1)
    modules: tuple[str, ...] = ()
    classes: tuple[str, ...] = ()
    allowed_path_prefixes: tuple[str, ...] = ()
