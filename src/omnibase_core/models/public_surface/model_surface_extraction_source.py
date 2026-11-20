# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One place a surface kind is read from, and how."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SURFACE_PARSERS: tuple[str, ...] = (
    "python_ast",
    "yaml_key_path",
    "toml_key_path",
    "text_literal",
)
_KEY_PATH_PARSERS = frozenset({"yaml_key_path", "toml_key_path"})


class ModelSurfaceExtractionSource(BaseModel):
    """Parser, include globs, key paths and reference forms for one source."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    parser: str
    include: tuple[str, ...] = Field(min_length=1)
    key_paths: tuple[str, ...] = ()
    reference_forms: tuple[str, ...] = ()

    @field_validator("parser")
    @classmethod
    def _known_parser(cls, value: str) -> str:
        if value not in SURFACE_PARSERS:
            raise ValueError(
                f"unknown parser '{value}'; expected one of {', '.join(SURFACE_PARSERS)}"
            )
        return value

    @model_validator(mode="after")
    def _key_paths_for_key_path_parsers(self) -> ModelSurfaceExtractionSource:
        if self.parser in _KEY_PATH_PARSERS and not self.key_paths:
            raise ValueError(f"parser '{self.parser}' needs at least one key path")
        return self
