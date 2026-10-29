# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorValidatorHome -- K7 ``validator_home`` entry (OMN-21503).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_validator_home`:
reads the file, builds typed facts, hands them to the pure checker. Run it in
every repository but omnibase_core; validator logic lives in core only.

    python -m omnibase_core.validation.validator_validator_home [paths...]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_validator_home_contract_fact import (
    ModelValidatorHomeContractFact,
)
from omnibase_core.models.validation.model_validator_home_hook_fact import (
    ModelValidatorHomeHookFact,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_rule_parameters import rule_strings
from omnibase_core.validation.checker_validator_home import (
    RULE_LOCAL_HOOK,
    RULE_NODE,
    RULE_PINNING_TEST,
    RULE_PYTEST_HOOK,
    RULE_SCRIPT_HOOK,
    check_hooks,
    check_node,
    check_test_file,
)
from omnibase_core.validation.validator_base import ValidatorBase


class ValidatorValidatorHome(ValidatorBase):
    """Refuse validator logic that lives outside omnibase_core."""

    validator_id: ClassVar[str] = "validator_home"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        rules = {r.rule_id: r for r in contract.rules}
        if self._matches(
            rules,
            (RULE_LOCAL_HOOK, RULE_SCRIPT_HOOK, RULE_PYTEST_HOOK),
            "config_name_patterns",
            path,
        ):
            return check_hooks(path, _read_hooks(path), rules)
        if self._matches(rules, (RULE_NODE,), "contract_name_patterns", path):
            return check_node(path, _read_node(path), rules)
        if self._matches(rules, (RULE_PINNING_TEST,), "test_name_patterns", path):
            return check_test_file(path, _read_text(path), rules)
        return ()

    @staticmethod
    def _matches(
        rules: dict[str, ModelValidatorRule],
        rule_ids: tuple[str, ...],
        key: str,
        path: Path,
    ) -> bool:
        return any(
            re.search(pattern, path.as_posix())
            for rule_id in rule_ids
            if rule_id in rules and rules[rule_id].enabled
            for pattern in rule_strings(rules[rule_id], key)
        )


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_hooks(path: Path) -> tuple[ModelValidatorHomeHookFact, ...]:
    data = load_yaml_mapping_no_duplicates(_read_text(path), source=str(path))
    repos = data.get("repos", [])
    hooks: list[ModelValidatorHomeHookFact] = []
    for repo in repos if isinstance(repos, list) else []:
        if not isinstance(repo, dict):
            continue
        for hook in repo.get("hooks", []) or []:
            if isinstance(hook, dict):
                hooks.append(
                    ModelValidatorHomeHookFact(
                        hook_id=str(hook.get("id", "")),
                        repo=str(repo.get("repo", "")),
                        language=str(hook.get("language", "")),
                        entry=str(hook.get("entry", "")),
                    )
                )
    return tuple(hooks)


def _read_node(path: Path) -> ModelValidatorHomeContractFact:
    data = load_yaml_mapping_no_duplicates(_read_text(path), source=str(path))
    output = data.get("output_model", "")
    if isinstance(output, dict):
        output = output.get("name", "")
    sources = tuple(_read_text(p) for p in sorted(path.parent.rglob("*.py")))
    return ModelValidatorHomeContractFact(
        directory_name=path.parent.name,
        contract_name=str(data.get("name", "")),
        output_model=str(output),
        handler_sources=sources,
    )


if __name__ == "__main__":
    sys.exit(ValidatorValidatorHome.main())
