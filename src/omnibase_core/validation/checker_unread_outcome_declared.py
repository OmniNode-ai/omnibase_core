# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``unread_outcome_declared`` (OMN-24538, fail-open ratchets).

A node contract whose ``io_operations`` declare an external read must carry a top-level
``unread_outcome`` mapping naming what a failed or absent read yields and the test that holds the
handler to that declaration; an external read whose unread outcome is undeclared is a fail-open --
the unread input silently becomes a value the caller never chose. Facts in (one contract's path and
source, plus a resolver that returns a named test file's source or ``None`` when the file does not
exist), ``ModelValidationIssue`` out. The read types, the key names, the test separator, the
annotation marker and the reason and remediation texts are ``parameters`` of the
``unread_outcome_declared`` rule row of ``contracts/unread_outcome_declared.validation.yaml``; an
enabled row with a missing or mistyped parameter raises, so a broken contract fails to load instead
of passing every file. Source that does not parse or is not a mapping is a finding, never clean. No
file read, no clock, no environment.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from pathlib import Path

import yaml

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_detector_common import (
    detector_issue,
    is_annotated,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

RULE_UNREAD_OUTCOME_DECLARED = "unread_outcome_declared"


def check_unread_outcome_declared(
    path: Path,
    source: str,
    resolve_test: Callable[[str], str | None],
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one contract under the ``unread_outcome_declared`` row, ordered by line.

    ``resolve_test`` returns the source of a repo-relative test file, or ``None`` when the file
    does not exist. A contract that declares no external read is judged clean; a contract that
    declares one must carry the ``unread_outcome`` mapping.
    """
    row = rules.get(RULE_UNREAD_OUTCOME_DECLARED)
    if row is None or not row.enabled:
        return ()
    read_types = frozenset(rule_strings(row, "external_read_types"))
    io_key = rule_string(row, "io_operations")
    op_type_key = rule_string(row, "operation_type")
    outcome_key = rule_string(row, "unread_outcome")
    returns_key = rule_string(row, "returns")
    test_key = rule_string(row, "test")
    separator = rule_string(row, "test_separator")
    marker = rule_string(row, "comment_prefix") + rule_string(row, "annotation_marker")
    reason = rule_string(row, "reason")
    remediation = rule_string(row, "remediation")

    lines = source.splitlines()
    lineno = _io_line(lines, io_key)
    issues: list[ModelValidationIssue] = []

    def finding(detail: str) -> None:
        if is_annotated(lines, lineno, marker):
            return
        issues.append(
            detector_issue(
                row,
                path,
                lines,
                lineno,
                f"{reason} ({detail})",
                remediation,
            )
        )

    try:
        contract = load_yaml_mapping_no_duplicates(
            source, source=RULE_UNREAD_OUTCOME_DECLARED
        )
    except (yaml.YAMLError, ValueError):
        finding("the contract does not parse as a YAML mapping")
        return tuple(issues)

    operations = contract.get(io_key)
    if operations is not None and not isinstance(operations, list):
        finding(f"{io_key} is not a list")
        return tuple(issues)
    declares_external_read = False
    for entry in operations or ():
        if not isinstance(entry, Mapping):
            finding(f"an {io_key} entry is not a mapping")
            continue
        operation = entry.get(op_type_key)
        if isinstance(operation, str) and operation in read_types:
            declares_external_read = True
    if not declares_external_read:
        return tuple(issues)

    outcome = contract.get(outcome_key)
    if not isinstance(outcome, Mapping):
        finding(f"the top level carries no {outcome_key} mapping")
        return tuple(issues)
    returns = outcome.get(returns_key)
    if not isinstance(returns, str) or not returns.strip():
        finding(f"{outcome_key} carries no non-empty {returns_key}")
    named = _named_test(outcome.get(test_key), separator)
    if named is None:
        finding(
            f"{outcome_key} carries no {test_key} of the form "
            f"<repo-relative file>{separator}<function>"
        )
        return tuple(issues)
    test_file, test_function = named
    test_source = resolve_test(test_file)
    if test_source is None:
        finding(f"the {test_key} file {test_file} does not exist")
    elif f"def {test_function}" not in test_source:
        finding(f"the {test_key} file {test_file} defines no function {test_function}")
    return tuple(sorted(issues, key=lambda i: i.line_number or 0))


def _io_line(lines: list[str], io_key: str) -> int:
    """The 1-based line ``io_key:`` stands on (first match at the start of a line), else 1."""
    pattern = re.compile(rf"^{re.escape(io_key)}:")
    return next((n for n, line in enumerate(lines, 1) if pattern.match(line)), 1)


def _named_test(test: object, separator: str) -> tuple[str, str] | None:
    """(file, function) from ``<file><separator><function>``; ``None`` when missing or malformed."""
    if not isinstance(test, str):
        return None
    file, _, function = test.rpartition(separator)
    if not file or not function:
        return None
    return (file, function)


__all__ = ["RULE_UNREAD_OUTCOME_DECLARED", "check_unread_outcome_declared"]
