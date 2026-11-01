# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic file validator for the pin needs/provides check (OMN-21879)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.pin_needs_provides.model_pin_needs_declaration import (
    ModelPinNeedsDeclaration,
)
from omnibase_core.models.pin_needs_provides.model_pin_needs_provides_check_input import (
    ModelPinNeedsProvidesCheckInput,
)
from omnibase_core.models.pin_needs_provides.model_pin_needs_provides_rules import (
    ModelPinNeedsProvidesRules,
)
from omnibase_core.models.pin_needs_provides.model_pin_provides_declaration import (
    ModelPinProvidesDeclaration,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_pin_needs_provides import (
    check_pin_needs_provides,
)
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorPinNeedsProvides"]


def _declaration(path: Path) -> dict[object, object]:
    """A declaration file's mapping; an absent file declares nothing."""
    if not path.is_file():
        return {}
    return load_yaml_mapping_no_duplicates(
        path.read_text(encoding="utf-8"), source=path.as_posix()
    )


class ValidatorPinNeedsProvides(ValidatorBase):
    """Read one caller file or diff and judge its verifier pins with the pure checker.

    The declarations are read from the paths the contract names, relative to the working
    directory (the repository root under pre-commit). An absent needs file names no
    verifier pin key; an absent provides file leaves every caller undeclared, so every
    verifier pin is refused. A malformed declaration raises rather than passing.
    """

    validator_id: ClassVar[str] = "pin_needs_provides"

    def _get_contract_path(self) -> Path:
        """Find the committed contract alongside the base validator's contracts."""
        return (
            Path(validator_base.__file__).parent
            / "contracts"
            / "pin_needs_provides.validation.yaml"
        )

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ()
        try:
            source_name = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            source_name = path.as_posix()
        rules = ModelPinNeedsProvidesRules.from_contract(contract)
        needs_path = rules.row("needs_undeclared").texts["needs_declaration_path"]
        provides_path = rules.row("provides_undeclared").texts[
            "provides_declaration_path"
        ]
        result = check_pin_needs_provides(
            ModelPinNeedsProvidesCheckInput(
                source_name=source_name,
                text=text,
                needs=ModelPinNeedsDeclaration.model_validate(
                    _declaration(Path(needs_path))
                ),
                provides=ModelPinProvidesDeclaration.model_validate(
                    _declaration(Path(provides_path))
                ),
                contract=contract,
            )
        )
        return tuple(
            issue.model_copy(update={"file_path": path}) for issue in result.issues
        )


if __name__ == "__main__":
    sys.exit(ValidatorPinNeedsProvides.main())
