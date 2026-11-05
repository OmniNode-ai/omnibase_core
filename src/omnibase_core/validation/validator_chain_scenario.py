# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Corpus-level ValidatorBase entry for the chain scenario checker (OMN-22478)."""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_receipt_set import (
    ModelChainScenarioReceiptSet,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_chain_scenario import check_chain_scenarios
from omnibase_core.validation.checker_rule_parameters import rule_string
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorChainScenario"]


class ValidatorChainScenario(ValidatorBase):
    """Read contracts strictly and judge each node's typed chain scenarios."""

    validator_id: ClassVar[str] = "chain_scenario"

    @staticmethod
    def _receipts_for(
        path: Path, contract: ModelValidatorSubcontract
    ) -> ModelChainScenarioReceiptSet | None:
        """The kept receipts beside a contract, or None when the file is absent."""
        file_name = next(
            (
                rule_string(rule, "receipts_file")
                for rule in contract.rules
                if rule.enabled
                and (rule.parameters or {}).get("kind") == "mutation_receipts"
            ),
            None,
        )
        if file_name is None:
            return None
        receipts_path = path.parent / file_name
        if not receipts_path.is_file():
            return None
        try:
            return ModelChainScenarioReceiptSet.model_validate_json(
                receipts_path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, ValidationError) as exc:
            raise ModelOnexError(
                message=f"{receipts_path}: cannot load mutation receipts: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc

    def _check_corpus(
        self, paths: Sequence[Path], contract: ModelValidatorSubcontract
    ) -> list[ModelValidationIssue]:
        documents: dict[str, dict[str, object]] = {}
        receipts: dict[str, ModelChainScenarioReceiptSet | None] = {}
        for path in paths:
            key = path.as_posix()
            try:
                document = load_yaml_mapping_no_duplicates(
                    path.read_text(encoding="utf-8"), source=key
                )
            except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
                raise ModelOnexError(
                    message=f"{path}: cannot load contract: {exc}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                ) from exc
            documents[key] = {str(k): v for k, v in document.items()}
            receipts[key] = self._receipts_for(path, contract)
        return check_chain_scenarios(documents, receipts, contract.rules)

    def validate(self, targets: Path | list[Path]) -> ModelValidationResult[None]:
        """Judge the complete resolved corpus once, then build the shared result."""
        start = time.monotonic()
        paths = self._resolve_targets(
            [targets] if isinstance(targets, Path) else targets
        )
        paths = [path for path in paths if not self._is_excluded(path)]
        issues = self._check_corpus(paths, self.contract)
        return self._build_result(
            files_checked=paths,
            issues=issues,
            files_with_violations=sorted({str(issue.file_path) for issue in issues}),
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        return tuple(self._check_corpus([path], contract))
