# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed projection of invariant-relevant fields in a required-check manifest."""

from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, field_validator


class ModelRequiredContextProducerManifestFields(BaseModel):
    """Require the gates collection without modeling unrelated manifest metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    gates: tuple[dict[str, object], ...]

    @field_validator("gates", mode="before")
    @classmethod
    def require_gates_list(cls, value: object) -> object:
        """A YAML set or mapping is not the required gates list."""
        if not isinstance(value, list):
            raise ValueError("manifest must contain a gates list")
        return value

    @classmethod
    def from_yaml(cls, text: str | None) -> Self:
        """Parse YAML text and validate the gates projection, without I/O."""
        document: object = yaml.safe_load(text) if text is not None else None
        if isinstance(document, dict):
            return cls.model_validate({"gates": document.get("gates")})
        return cls.model_validate(document)
