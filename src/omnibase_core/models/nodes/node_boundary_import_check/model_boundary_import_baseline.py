# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strict YAML schema for the shrink-only edge list."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class ModelBoundaryImportBaseline(BaseModel):
    """Only sorted unique edge identities from OMN-17427 are accepted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1]
    gate: Literal["OMN-17427"]
    edges: list[str]

    @field_validator("schema_version", mode="before")
    @classmethod
    def validate_version(cls, value: object) -> object:
        """Do not accept YAML booleans or floats as version 1."""
        if type(value) is not int:
            raise ValueError("schema_version must be the integer 1")
        return value

    @field_validator("edges")
    @classmethod
    def validate_edges(cls, value: list[str]) -> list[str]:
        """Reject duplicate, unsorted or malformed identities."""
        if value != sorted(set(value)):
            raise ValueError("edges must be sorted and unique")
        for edge in value:
            parts = edge.split(" -> ")
            if len(parts) != 2 or any(
                not part or part.strip() != part or "\n" in part or "\r" in part
                for part in parts
            ):
                raise ValueError(f"malformed edge identity: {edge!r}")
        return value
