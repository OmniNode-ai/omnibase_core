# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The public-surface contract: one extraction rule per kind."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_public_surface_kind import EnumPublicSurfaceKind
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.public_surface.model_surface_extraction_rule import (
    ModelSurfaceExtractionRule,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates


def _describe(loc: tuple[int | str, ...], msg: str) -> str:
    """Render a pydantic location as ``rules[1].sources[1].parser: msg``."""
    if loc[:1] != ("rules",) or len(loc) < 2:
        return msg
    path = "rules"
    for part in loc[1:]:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return f"{path}: {msg}"


class ModelPublicSurfaceContract(BaseModel):
    """The list of rules; two rules may not name the same kind."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rules: tuple[ModelSurfaceExtractionRule, ...]

    @model_validator(mode="after")
    def _one_rule_per_kind(self) -> ModelPublicSurfaceContract:
        seen: dict[EnumPublicSurfaceKind, int] = {}
        for index, rule in enumerate(self.rules):
            if rule.kind in seen:
                raise ValueError(
                    f"rules[{seen[rule.kind]}] and rules[{index}] both name kind "
                    f"'{rule.kind.value}'"
                )
            seen[rule.kind] = index
        return self

    @classmethod
    def from_validation_document(
        cls, document: Mapping[object, object]
    ) -> ModelPublicSurfaceContract:
        """Build from a parsed *.validation.yaml document; errors name the row."""
        validation = document.get("validation")
        rows = validation.get("rules") if isinstance(validation, dict) else None
        if not isinstance(rows, list):
            raise ModelOnexError(
                message="validation.rules must be a list",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        rules: list[dict[str, object]] = []
        for index, row in enumerate(rows):
            params = row.get("parameters") if isinstance(row, dict) else None
            if not isinstance(params, dict):
                raise ModelOnexError(
                    message=f"rules[{index}]: parameters must be a mapping",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            rules.append(dict(params))
        try:
            return cls.model_validate({"rules": rules})
        except ValidationError as exc:
            parts = [_describe(err["loc"], str(err["msg"])) for err in exc.errors()]
            raise ModelOnexError(
                message="; ".join(parts),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc

    @classmethod
    def from_validation_file(cls, path: Path) -> ModelPublicSurfaceContract:
        """Load the contract from a *.validation.yaml file."""
        document = load_yaml_mapping_no_duplicates(
            path.read_text(encoding="utf-8"), source=str(path)
        )
        return cls.from_validation_document(document)
