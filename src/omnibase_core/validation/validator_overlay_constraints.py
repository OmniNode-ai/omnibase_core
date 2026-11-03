# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic file validator for overlay constraints (OMN-22185)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.overlay_constraints.model_overlay_constraints_check_input import (
    ModelOverlayConstraintsCheckInput,
)
from omnibase_core.models.overlay_constraints.model_overlay_constraints_declaration import (
    ModelOverlayConstraintsDeclaration,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_overlay_constraints import (
    check_overlay_constraints,
)
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorOverlayConstraints"]


def _flatten(values: object, source: str) -> dict[str, object]:
    """Overlay name to key to value, flattened to key to value; a key set twice to two values raises."""
    if not isinstance(values, dict):
        raise ModelOnexError(
            message=f"{source}: overlay_values must map overlay names to key mappings",
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        )
    flat: dict[str, object] = {}
    for overlay, keys in values.items():
        if not isinstance(keys, dict):
            raise ModelOnexError(
                message=f"{source}: overlay {overlay!r} must be a mapping of keys to values",
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
            )
        for key, value in keys.items():
            if key in flat and flat[key] != value:
                raise ModelOnexError(
                    message=f"{source}: overlay key {key!r} is set to two different values",
                    error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                )
            flat[str(key)] = value
    return flat


class ValidatorOverlayConstraints(ValidatorBase):
    """Read one contract file and judge its overlay values against its declared relations.

    A file with no ``overlay_constraints`` block is not judged. A file with the block and no
    ``overlay_values`` is judged against an empty overlay, so every key a relation names is
    absent. A malformed block or values mapping raises rather than passing.
    """

    validator_id: ClassVar[str] = "overlay_constraints"

    def _get_contract_path(self) -> Path:
        """Find the committed contract alongside the base validator's contracts."""
        return (
            Path(validator_base.__file__).parent
            / "contracts"
            / "overlay_constraints.validation.yaml"
        )

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ()
        document = load_yaml_mapping_no_duplicates(text, source=path.as_posix())
        if "overlay_constraints" not in document:
            return ()
        try:
            source_name = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            source_name = path.as_posix()
        result = check_overlay_constraints(
            ModelOverlayConstraintsCheckInput(
                source_name=source_name,
                declaration=ModelOverlayConstraintsDeclaration.model_validate(
                    document["overlay_constraints"]
                ),
                values=_flatten(document.get("overlay_values", {}), source_name),
                contract=contract,
            )
        )
        return tuple(
            issue.model_copy(update={"file_path": path}) for issue in result.issues
        )


if __name__ == "__main__":
    sys.exit(ValidatorOverlayConstraints.main())
