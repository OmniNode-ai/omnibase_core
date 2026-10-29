# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Numeric-threshold rule of the contract-config-compliance validator (OMN-21503).

A module- or class-level constant whose name the rule's ``name_pattern`` matches and
that holds a number other than 0 or 1 is a hard-coded threshold: thresholds are
contract or overlay data. The pattern and the baseline path are the rule's
parameters in contract_config_compliance.validation.yaml; this module holds none.
"""

from __future__ import annotations

import ast
import re
from functools import lru_cache
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_contract_config_compliance_finding import (
    ModelContractConfigComplianceFinding,
)
from omnibase_core.models.validation.model_validator_contract_file import (
    ModelValidatorContractFile,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = [
    "EXCLUDED_PATH_PARTS",
    "THRESHOLD_RULE_ID",
    "file_threshold_findings",
    "load_packaged_contract",
    "threshold_findings",
    "threshold_rule",
]

THRESHOLD_RULE_ID = "hardcoded_threshold"
EXCLUDED_PATH_PARTS: frozenset[str] = frozenset(
    {
        ".venv",
        "__pycache__",
        "build",
        "dist",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "node_modules",
        ".git",
        "archived",
        "archive",
    }
)
_CONTRACTS_DIR = Path(__file__).parents[1] / "validation" / "contracts"


def load_contract_text(content: str) -> ModelValidatorSubcontract:
    """Parse a ``*.validation.yaml`` document."""
    return load_yaml_content_as_model(content, ModelValidatorContractFile).validation


@lru_cache(maxsize=8)
def load_packaged_contract(validator_id: str) -> ModelValidatorSubcontract:
    """The packaged contract of a validator, by id."""
    path = _CONTRACTS_DIR / f"{validator_id}.validation.yaml"
    return load_contract_text(path.read_text(encoding="utf-8"))


def threshold_rule(contract: ModelValidatorSubcontract) -> ModelValidatorRule | None:
    """The enabled threshold rule of a contract, if it has one."""
    return next(
        (r for r in contract.rules if r.rule_id == THRESHOLD_RULE_ID and r.enabled),
        None,
    )


def threshold_findings(
    *,
    path: Path,
    tree: ast.Module,
    lines: list[str],
    rule: ModelValidatorRule,
    suppression_marker: str,
) -> list[ModelContractConfigComplianceFinding]:
    """Constant numeric assignments in module and class scopes that are thresholds."""
    pattern = (rule.parameters or {}).get("name_pattern")
    if not isinstance(pattern, str):
        raise ModelOnexError(
            message="Threshold policy requires name_pattern",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    name_pattern = re.compile(pattern)
    findings: list[ModelContractConfigComplianceFinding] = []

    class _Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self._in_function = False

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_function(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._visit_function(node)

        def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            previous = self._in_function
            self._in_function = True
            self.generic_visit(node)
            self._in_function = previous

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            previous = self._in_function
            self._in_function = False
            self.generic_visit(node)
            self._in_function = previous

        def visit_Assign(self, node: ast.Assign) -> None:
            self.check(node, node.targets, node.value)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            self.check(node, [node.target], node.value)

        def check(
            self,
            node: ast.Assign | ast.AnnAssign,
            targets: list[ast.expr],
            value: ast.expr | None,
        ) -> None:
            if self._in_function:
                return
            sign = 1
            if isinstance(value, ast.UnaryOp) and isinstance(
                value.op, (ast.USub, ast.UAdd)
            ):
                sign = -1 if isinstance(value.op, ast.USub) else 1
                value = value.operand
            if not isinstance(value, ast.Constant):
                return
            number = value.value
            if isinstance(number, bool) or not isinstance(number, (int, float)):
                return
            if sign * number in (0, 1) or suppression_marker in lines[node.lineno - 1]:
                return
            for target in targets:
                if isinstance(target, ast.Name) and name_pattern.fullmatch(target.id):
                    findings.append(
                        ModelContractConfigComplianceFinding(
                            path=path,
                            line=node.lineno,
                            column=node.col_offset,
                            rule=rule.rule_id,
                            message=(
                                f"numeric threshold {target.id} must be declared "
                                "in a contract or overlay"
                            ),
                        )
                    )

    _Visitor().visit(tree)
    return findings


def file_threshold_findings(
    path: Path, tree: ast.Module, lines: list[str], suppression_marker: str
) -> list[ModelContractConfigComplianceFinding]:
    """Threshold findings of one parsed file under the packaged contract's rule."""
    rule = threshold_rule(load_packaged_contract("contract_config_compliance"))
    if rule is None:
        return []
    return threshold_findings(
        path=path,
        tree=tree,
        lines=lines,
        rule=rule,
        suppression_marker=suppression_marker,
    )
