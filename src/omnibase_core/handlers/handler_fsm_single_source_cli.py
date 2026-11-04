# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorFsmSingleSource -- file-system boundary of the FSM single-source check (OMN-21513).

Reads each reducer ``contract.yaml`` and the Python under its directory, hands the texts to
``HandlerFsmSingleSource`` and returns its issues. The contract is
``validation/contracts/fsm_single_source.validation.yaml``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from omnibase_core.handlers.handler_fsm_single_source import HandlerFsmSingleSource
from omnibase_core.handlers.handler_fsm_single_source_rules import (
    node_type_prefix_from_subcontract,
    rules_from_subcontract,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_fsm_single_source_request import (
    ModelFsmSingleSourceRequest,
)
from omnibase_core.models.validation.model_fsm_source_text import ModelFsmSourceText
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorFsmSingleSource", "main"]


class ValidatorFsmSingleSource(ValidatorBase):
    """Require reducer contracts to own their state machines exclusively."""

    validator_id = "fsm_single_source"

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        if path.name != "contract.yaml":
            return ()
        try:
            text = path.read_text(encoding="utf-8")
            document = load_yaml_mapping_no_duplicates(text, source=str(path))
        except (OSError, ValueError, yaml.YAMLError):
            return ()
        prefix = node_type_prefix_from_subcontract(contract)
        if prefix is None:
            return ()
        node_type = document.get("node_type")
        if not isinstance(node_type, str) or not node_type.upper().startswith(prefix):
            return ()
        sources = tuple(
            ModelFsmSourceText(
                name=str(source), text=source.read_text(encoding="utf-8")
            )
            for source in sorted(path.parent.rglob("*.py"))
            if "__pycache__" not in source.relative_to(path.parent).parts
        )
        return (
            HandlerFsmSingleSource()
            .handle(
                ModelFsmSingleSourceRequest(
                    contract_source=ModelFsmSourceText(name=str(path), text=text),
                    sources=sources,
                    rules=rules_from_subcontract(contract),
                )
            )
            .issues
        )

    def _get_contract_path(self) -> Path:
        return (
            Path(__file__).resolve().parent.parent
            / "validation"
            / "contracts"
            / f"{self.validator_id}.validation.yaml"
        )


def main() -> int:
    return ValidatorFsmSingleSource.main()


if __name__ == "__main__":
    sys.exit(main())
