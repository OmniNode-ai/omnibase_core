# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for K7 ``validator_home`` (OMN-21503).

Validator logic lives in omnibase_core only. Facts in (the hooks of one
pre-commit config, one node contract with its handler sources, one test file),
``ModelValidationIssue`` out: no file read, no clock, no environment. Every
pattern, name list and marker is a ``parameters`` entry of the matching rule row
in ``contracts/validator_home.validation.yaml``; this module holds none.

Rules: validator_node_outside_core, local_hook_definition, repo_script_hook,
pytest_hook, config_pinning_test.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.validation.model_validator_home_contract_fact import (
    ModelValidatorHomeContractFact,
)
from omnibase_core.models.validation.model_validator_home_hook_fact import (
    ModelValidatorHomeHookFact,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_string,
    rule_strings,
)

RULE_NODE = "validator_node_outside_core"
RULE_LOCAL_HOOK = "local_hook_definition"
RULE_SCRIPT_HOOK = "repo_script_hook"
RULE_PYTEST_HOOK = "pytest_hook"
RULE_PINNING_TEST = "config_pinning_test"


def _issue(
    rule: ModelValidatorRule, path: Path, message: str, line: int | None = None
) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=rule.severity,
        message=message,
        code=rule.rule_id,
        file_path=path,
        line_number=line,
        rule_name=rule.rule_id,
    )


def _active(rules: Mapping[str, ModelValidatorRule], rule_id: str) -> bool:
    row = rules.get(rule_id)
    return row is not None and row.enabled


def _any_match(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def check_hooks(
    path: Path,
    hooks: tuple[ModelValidatorHomeHookFact, ...],
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """One issue per offending hook, under the most specific enabled rule.

    A hook that runs a repository script is a repo_script_hook, one that runs
    pytest a pytest_hook, any other local definition a local_hook_definition.
    """
    issues: list[ModelValidationIssue] = []
    for hook in hooks:
        issue = _hook_issue(path, hook, rules)
        if issue is not None:
            issues.append(issue)
    return tuple(issues)


def _hook_issue(
    path: Path,
    hook: ModelValidatorHomeHookFact,
    rules: Mapping[str, ModelValidatorRule],
) -> ModelValidationIssue | None:
    if _active(rules, RULE_SCRIPT_HOOK):
        row = rules[RULE_SCRIPT_HOOK]
        if _any_match(rule_strings(row, "script_entry_patterns"), hook.entry):
            return _issue(
                row,
                path,
                f"hook {hook.hook_id!r} runs a repository script: {row.description}",
            )
    if _active(rules, RULE_PYTEST_HOOK):
        row = rules[RULE_PYTEST_HOOK]
        if _any_match(rule_strings(row, "pytest_entry_patterns"), hook.entry):
            return _issue(
                row, path, f"hook {hook.hook_id!r} runs pytest: {row.description}"
            )
    if _active(rules, RULE_LOCAL_HOOK):
        row = rules[RULE_LOCAL_HOOK]
        if hook.repo == rule_string(row, "local_repo_value") and (
            hook.language in rule_strings(row, "local_languages")
            or _any_match(rule_strings(row, "inline_shell_patterns"), hook.entry)
        ):
            return _issue(
                row,
                path,
                f"local hook {hook.hook_id!r} defines a check: {row.description}",
            )
    return None


def check_node(
    path: Path,
    node: ModelValidatorHomeContractFact,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """One issue for a validator node outside core that holds its own predicate."""
    if not _active(rules, RULE_NODE):
        return ()
    row = rules[RULE_NODE]
    is_validator = node.output_model.rsplit(".", 1)[-1] in rule_strings(
        row, "validator_output_models"
    ) or any(
        _any_match(rule_strings(row, "validator_node_patterns"), name)
        for name in (node.directory_name, node.contract_name)
    )
    if not is_validator:
        return ()
    imports_core_checker = any(
        _any_match(rule_strings(row, "core_checker_import_patterns"), source)
        for source in node.handler_sources
    )
    defines_predicate = any(
        _any_match(rule_strings(row, "predicate_patterns"), source)
        for source in node.handler_sources
    )
    if imports_core_checker and not defines_predicate:
        return ()
    return (
        _issue(
            row,
            path,
            f"node {node.directory_name!r} is a validator outside core: {row.description}",
        ),
    )


def check_test_file(
    path: Path,
    text: str,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """One issue for a test that pins hook or workflow text, unless it is a canary."""
    if not _active(rules, RULE_PINNING_TEST):
        return ()
    row = rules[RULE_PINNING_TEST]
    if _any_match(rule_strings(row, "canary_patterns"), text):
        return ()
    lines = text.splitlines()
    config_lines = [
        n
        for n, line in enumerate(lines, start=1)
        if _any_match(rule_strings(row, "config_path_patterns"), line)
    ]
    if not config_lines:
        return ()
    if not _any_match(rule_strings(row, "text_assertion_patterns"), text):
        return ()
    return (
        _issue(
            row,
            path,
            f"test pins hook or workflow text: {row.description}",
            config_lines[0],
        ),
    )


__all__ = [
    "RULE_LOCAL_HOOK",
    "RULE_NODE",
    "RULE_PINNING_TEST",
    "RULE_PYTEST_HOOK",
    "RULE_SCRIPT_HOOK",
    "check_hooks",
    "check_node",
    "check_test_file",
]
