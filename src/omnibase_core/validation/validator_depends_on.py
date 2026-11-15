# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic file validator for the depends-on check (OMN-24537)."""

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
from omnibase_core.models.depends_on.model_depends_on_check_input import (
    ModelDependsOnCheckInput,
)
from omnibase_core.models.depends_on.model_depends_on_facts import ModelDependsOnFacts
from omnibase_core.models.depends_on.model_depends_on_rules import ModelDependsOnRules
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_depends_on import check_depends_on
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorDependsOn"]


def read_facts(path: Path) -> ModelDependsOnFacts | None:
    """The facts file at a path; an absent file supplies no facts, an unreadable or malformed one raises."""
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ModelOnexError(
            message=f"depends-on facts file {path.as_posix()} is unreadable",
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
        ) from exc
    return ModelDependsOnFacts.model_validate(
        load_yaml_mapping_no_duplicates(text, source=path.as_posix())
    )


class ValidatorDependsOn(ValidatorBase):
    """Read one contract, ticket contract or unit declaration and judge its declared dependencies.

    The facts come from the file the contract names, relative to the working directory (the
    repository root under pre-commit). An absent file supplies no facts, so every declared dependency
    is refused; a present file that is unreadable or malformed raises rather than passing.
    """

    validator_id: ClassVar[str] = "depends_on"

    def _get_contract_path(self) -> Path:
        """Find the committed contract alongside the base validator's contracts."""
        return (
            Path(validator_base.__file__).parent
            / "contracts"
            / "depends_on.validation.yaml"
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
        facts_path = (
            ModelDependsOnRules.from_contract(contract)
            .row("facts_unsupplied")
            .texts["facts_file_path"]
        )
        result = check_depends_on(
            ModelDependsOnCheckInput(
                source_name=source_name,
                text=text,
                facts=read_facts(Path(facts_path)),
                contract=contract,
            )
        )
        return tuple(
            issue.model_copy(update={"file_path": path}) for issue in result.issues
        )


if __name__ == "__main__":
    sys.exit(ValidatorDependsOn.main())
