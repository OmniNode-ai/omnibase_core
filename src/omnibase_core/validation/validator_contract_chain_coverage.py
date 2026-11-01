# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strict corpus loader and AST binding scanner for contract-chain coverage.

Use the generic validation-report runtime with ValidatorContractChainCoverage.
Paths in evidence and obligation IDs are relative to the current working
directory when possible, otherwise absolute POSIX paths.
"""

from __future__ import annotations

import ast
import fnmatch
import json
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
from omnibase_core.models.validation.model_contract_chain_binding import (
    ModelContractChainBinding,
)
from omnibase_core.models.validation.model_contract_chain_facts import (
    ModelContractChainFacts,
)
from omnibase_core.models.validation.model_contract_chain_generated_case import (
    ModelContractChainGeneratedCase,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_contract_chain_coverage import (
    check_contract_chain_coverage,
    coverage_settings,
    validate_rules,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.validator_contract_walker import load_machines


def _key(path: Path) -> str:
    resolved = path.resolve()
    return (
        resolved.relative_to(Path.cwd()).as_posix()
        if resolved.is_relative_to(Path.cwd())
        else resolved.as_posix()
    )


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ModelOnexError(
            message=f"{path}: cannot read chain coverage input: {exc}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from exc


def _marker(decorator: ast.expr, name: str) -> str | None:
    if not isinstance(decorator, ast.Call):
        return None
    callee = decorator.func
    actual = (
        callee.id
        if isinstance(callee, ast.Name)
        else callee.attr
        if isinstance(callee, ast.Attribute)
        else None
    )
    if actual != name:
        return None
    if (
        len(decorator.args) != 1
        or decorator.keywords
        or not isinstance(decorator.args[0], ast.Constant)
        or not isinstance(decorator.args[0].value, str)
    ):
        raise ModelOnexError(
            message=f"{name} at line {decorator.lineno} requires one literal string argument",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return decorator.args[0].value


def _scan(
    path: Path, marker: str, overlay_marker: str
) -> list[ModelContractChainBinding]:
    try:
        tree = ast.parse(_read(path), filename=path.as_posix())
    except SyntaxError as exc:
        raise ModelOnexError(
            message=f"{path}: cannot parse chain test: {exc}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from exc
    bindings: list[ModelContractChainBinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        overlays = tuple(
            sorted(
                {
                    name
                    for decorator in node.decorator_list
                    if (name := _marker(decorator, overlay_marker)) is not None
                }
            )
        )
        for decorator in node.decorator_list:
            identity = _marker(decorator, marker)
            if identity is not None:
                bindings.append(
                    ModelContractChainBinding(
                        obligation_ref=identity,
                        file=_key(path),
                        line=decorator.lineno,
                        overlays=overlays,
                    )
                )
    return bindings


def load_facts(
    paths: Sequence[Path], contract: ModelValidatorSubcontract
) -> ModelContractChainFacts:
    """Read contracts, test ASTs and committed generated cases, without execution."""
    validate_rules(contract.rules)
    settings = coverage_settings(contract.rules)
    documents = {}
    fsms: dict[str, ModelFSMSubcontract] = {}
    for path in paths:
        key = _key(path)
        try:
            document = load_yaml_mapping_no_duplicates(_read(path), source=key)
            machines, _not_armed = load_machines([path])
        except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot load contract: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        documents[key] = {str(k): v for k, v in document.items()}
        for machine in machines:
            fsms[key] = machine.fsm
    test_paths: set[Path] = set()
    for root in rule_strings(settings, "test_roots"):
        for pattern in rule_strings(settings, "test_file_globs"):
            test_paths.update(
                path
                for path in Path(root).glob(pattern)
                if not any(
                    fnmatch.fnmatch(path.relative_to(root).as_posix(), excluded)
                    for excluded in rule_strings(settings, "test_exclude_patterns")
                )
            )
    bindings = []
    for path in sorted(test_paths):
        if path.is_file():
            bindings.extend(
                _scan(
                    path,
                    rule_string(settings, "marker_name"),
                    rule_string(settings, "overlay_marker_name"),
                )
            )
    for path in sorted(Path().glob(rule_string(settings, "generated_cases_glob"))):
        try:
            cases = json.loads(_read(path))
            if not isinstance(cases, list):
                raise ModelOnexError(
                    message="generated cases must be a JSON list",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            for index, item in enumerate(cases, start=1):
                case = ModelContractChainGeneratedCase.model_validate(item)
                bindings.append(
                    ModelContractChainBinding(
                        obligation_ref=case.obligation_ref,
                        file=_key(path),
                        line=index,
                        overlays=case.overlays,
                    )
                )
        except ValueError as exc:
            raise ModelOnexError(
                message=f"{path}: cannot load generated cases: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
    return ModelContractChainFacts.model_validate(
        {"documents": documents, "fsms": fsms, "bindings": tuple(bindings)}
    )


class ValidatorContractChainCoverage(ValidatorBase):
    """Judge the resolved corpus once through the generic validation runtime."""

    validator_id: ClassVar[str] = "contract_chain_coverage"

    def _check_corpus(
        self, paths: Sequence[Path], contract: ModelValidatorSubcontract
    ) -> list[ModelValidationIssue]:
        return check_contract_chain_coverage(
            load_facts(paths, contract), contract.rules
        )

    def validate(self, targets: Path | list[Path]) -> ModelValidationResult[None]:
        """Resolve contracts and preserve the checker's rule/owner/entity ordering."""
        start = time.monotonic()
        paths = self._resolve_targets(
            [targets] if isinstance(targets, Path) else targets
        )
        paths = [path for path in paths if not self._is_excluded(path)]
        issues = self._check_corpus(paths, self.contract)
        result = self._build_result(
            files_checked=paths,
            issues=issues,
            files_with_violations=sorted({str(issue.file_path) for issue in issues}),
            duration_ms=int((time.monotonic() - start) * 1000),
        )
        return result.model_copy(update={"issues": issues})

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        return tuple(self._check_corpus([path], contract))
