# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Global file-reading adapter for invariant analysis (OMN-21565)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import ClassVar, cast

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers._invariant_analysis_rules_interface import (
    InvariantAnalysisRulesInterface,
)
from omnibase_core.handlers.handler_invariant_analysis import HandlerInvariantAnalysis
from omnibase_core.handlers.handler_invariant_analysis_rules import (
    analyse_document,
    build_registry,
    is_exempt_by_lifecycle,
    matches_globs,
    parse_overlay,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.invariant_analysis.model_invariant_analysis_input import (
    ModelInvariantAnalysisInput,
)
from omnibase_core.models.invariant_analysis.model_invariant_analysis_rules import (
    ModelInvariantAnalysisRules,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorInvariantAnalysis", "build_analysis_container"]


def build_analysis_container() -> ModelONEXContainer:
    """Compose the container that supplies the pure rule function to the handler."""
    container = ModelONEXContainer(enable_service_registry=True)
    asyncio.run(
        container.service_registry.register_instance(
            cast(
                "type[InvariantAnalysisRulesInterface[ModelInvariantAnalysisInput, ModelInvariantAnalysisRules, tuple[ModelValidationFindingEmbed, ...]]]",
                InvariantAnalysisRulesInterface,
            ),
            analyse_document,
        )
    )
    return container


def _read_mapping(path: Path) -> Mapping[str, object]:
    raw = load_yaml_mapping_no_duplicates(
        path.read_text(encoding="utf-8"), source=str(path)
    )
    if not all(isinstance(key, str) for key in raw):
        raise ModelOnexError(
            message=f"{path}: mapping keys must be text",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return {str(key): value for key, value in raw.items()}


class ValidatorInvariantAnalysis(ValidatorBase):
    """Always scan the root corpus; passed filenames never limit coverage."""

    validator_id: ClassVar[str] = "invariant_analysis"

    def _load_contract(self) -> ModelValidatorSubcontract:
        contract = super()._load_contract()
        ModelInvariantAnalysisRules.from_contract(contract)
        return contract

    def validate(self, targets: Path | list[Path]) -> ModelValidationResult[None]:
        """Use a single directory target as root, otherwise use the working directory."""
        start = time.monotonic()
        paths = [targets] if isinstance(targets, Path) else targets
        root = paths[0] if len(paths) == 1 and paths[0].is_dir() else Path.cwd()
        issues, checked = self._check_corpus(root, self.contract)
        return self._build_result(
            files_checked=checked,
            issues=issues,
            files_with_violations=sorted({str(issue.file_path) for issue in issues}),
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    def _check_corpus(
        self, root: Path, contract: ModelValidatorSubcontract
    ) -> tuple[list[ModelValidationIssue], list[Path]]:
        rules = ModelInvariantAnalysisRules.from_contract(contract)
        registry_rule = rules.row("registry_invalid")
        try:
            overlay = parse_overlay(
                _read_mapping(root / registry_rule.texts["overlay_filename"])
            )
        except (OSError, UnicodeError, yaml.YAMLError, ValueError) as exc:
            raise ModelOnexError(
                message=f"Cannot read invariant analysis overlay: {exc}",
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
            ) from exc
        # The consuming repository, through its overlay, owns plan locations.
        bound = contract.model_copy(
            update={"target_patterns": list(overlay.plan_globs)}
        )
        registry_path = root / overlay.registry_path
        registry = None
        registry_error = None
        try:
            registry = build_registry(_read_mapping(registry_path), rules)
        except (
            OSError,
            UnicodeError,
            yaml.YAMLError,
            ValueError,
            ModelOnexError,
        ) as exc:
            registry_error = str(exc)
        handler = HandlerInvariantAnalysis(build_analysis_container())

        def check(path: str, text: str) -> list[ModelValidationIssue]:
            report = handler.handle(
                ModelInvariantAnalysisInput(
                    path=path,
                    text=text,
                    registry=registry,
                    registry_error=registry_error,
                    overlay=overlay,
                    contract=bound,
                )
            )
            return [
                ModelValidationIssue(
                    severity=rules.row(str(finding.rule_id)).severity,
                    message=finding.message,
                    rule_name=finding.rule_id,
                    code=finding.rule_id,
                    file_path=root / path,
                    suggestion=finding.remediation,
                )
                for finding in report.findings
            ]

        if registry is None:
            return check(overlay.registry_path, ""), [registry_path]
        try:
            lifecycle = _read_mapping(root / overlay.lifecycle_path)
        except (OSError, UnicodeError, yaml.YAMLError, ValueError) as exc:
            raise ModelOnexError(
                message=f"Cannot read invariant lifecycle: {exc}",
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
            ) from exc
        authority = rules.row("authority_doc_coverage")
        candidates = {
            path
            for pattern in (*overlay.plan_globs, authority.texts["markdown_glob"])
            for path in root.glob(pattern)
        }
        issues: list[ModelValidationIssue] = []
        checked: list[Path] = []
        for path in sorted(candidates):
            relative = path.relative_to(root).as_posix()
            if any(
                part in overlay.skip_dirs for part in PurePosixPath(relative).parts
            ) or matches_globs(relative, authority.lists["scan_exclusions"]):
                continue
            if not path.is_file():
                continue
            if matches_globs(relative, overlay.plan_globs) and is_exempt_by_lifecycle(
                relative, lifecycle, overlay, rules
            ):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise ModelOnexError(
                    message=f"Cannot read document {relative}: {exc}",
                    error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                ) from exc
            checked.append(path)
            issues.extend(check(relative, text))
        return issues, checked

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        """Retain the global scan even when invoked through the single-file API."""
        issues, _ = self._check_corpus(Path.cwd(), contract)
        return tuple(issues)
