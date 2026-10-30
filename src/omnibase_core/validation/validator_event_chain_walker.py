# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Corpus-level ValidatorBase entry for the event-chain checker (OMN-21558)."""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_event_chain_walker import check_event_chain
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.validator_contract_walker import load_machines

__all__ = ["ValidatorEventChainWalker"]


class ValidatorEventChainWalker(ValidatorBase):
    """Read contracts strictly and judge relations across the resolved corpus."""

    validator_id: ClassVar[str] = "event_chain_walker"

    def _check_corpus(
        self, paths: Sequence[Path], contract: ModelValidatorSubcontract
    ) -> list[ModelValidationIssue]:
        documents: dict[str, dict[str, object]] = {}
        fsms: dict[str, ModelFSMSubcontract] = {}
        for path in paths:
            key = path.as_posix()
            try:
                document = load_yaml_mapping_no_duplicates(
                    path.read_text(encoding="utf-8"), source=key
                )
                machines, _not_armed = load_machines([path])
            except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
                raise ModelOnexError(
                    message=f"{path}: cannot load contract: {exc}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                ) from exc
            documents[key] = {str(k): v for k, v in document.items()}
            for machine in machines:
                fsms[key] = machine.fsm
        return check_event_chain(documents, fsms, contract.rules)

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
