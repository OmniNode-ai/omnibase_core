# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Static action contract, including its effective configuration."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelErrorActionContract(BaseModel):
    """One registered action or a node in its declared static call closure."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        json_schema_extra={
            "oneOf": [
                {
                    "required": ["node"],
                    "properties": {
                        "node": {"type": "string", "minLength": 1},
                        "lane_kind": {"type": "null"},
                    },
                },
                {
                    "required": ["lane_kind"],
                    "properties": {
                        "lane_kind": {"type": "string", "minLength": 1},
                        "node": {"type": "null"},
                    },
                },
            ]
        },
    )

    id: str = Field(min_length=1)
    node: str | None = Field(default=None, min_length=1)
    lane_kind: str | None = Field(default=None, min_length=1)
    capabilities: tuple[str, ...]
    targets: tuple[str, ...] = Field(min_length=1)
    scope_marker: tuple[str, ...] = Field(min_length=1)
    receivers: tuple[str, ...]
    idempotent_by: tuple[str, ...] = Field(min_length=1)
    calls: tuple[str, ...]

    @model_validator(mode="after")
    def require_execution_binding(self) -> Self:
        """A contract binds one registered node or lane kind, never an ambiguous pair."""
        if (self.node is None) == (self.lane_kind is None):
            raise ValueError(
                "node or lane_kind: exactly one execution binding is required"
            )
        binding = self.node if self.node is not None else self.lane_kind
        if binding is not None and not binding.strip():
            raise ValueError("node or lane_kind: execution binding cannot be blank")
        return self
