# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorHardcodedTopics -- reject hardcoded ONEX topic string literals.

Detects two classes of violations:

1. **Topic literals** -- quoted strings matching ``onex.(cmd|evt|dlq).*``
2. **Env-var topics** -- assignments to ``*_TOPIC`` environment variables

Approved source-of-truth files (topic registries, contract YAML, topic enum
modules) are exempt.  Individual lines can be suppressed with marker comments.

Usage Examples:
    Programmatic usage::

        from pathlib import Path
        from omnibase_core.validation import ValidatorHardcodedTopics

        validator = ValidatorHardcodedTopics()
        result = validator.validate(Path("src/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI usage::

        python -m omnibase_core.validation.validator_hardcoded_topics src/

    Pre-commit hook::

        check-hardcoded-topics-v2  [files...]

Suppression:
    Add one of these markers anywhere on a line to suppress::

        # onex-topic-sot          -- source-of-truth declaration
        # onex-topic-test-fixture -- test fixture data
        # onex-topic-doc-example  -- documentation example
        # onex-topic-allow: <reason>  -- explicit override

Schema Version:
    v1.0.0 - Initial version (OMN-9152)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.handlers.handler_hardcoded_host_list import host_list_issues
from omnibase_core.handlers.handler_hardcoded_topics_approved_files import (
    APPROVED_BASENAMES as _APPROVED_BASENAMES,
)
from omnibase_core.handlers.handler_hardcoded_topics_approved_files import (
    APPROVED_SUFFIXES as _APPROVED_SUFFIXES,
)
from omnibase_core.handlers.handler_hardcoded_topics_approved_files import (
    EXCLUDED_PATH_PARTS as _EXCLUDED_PATH_PARTS,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.validator_base import ValidatorBase

_ONEX_TOPIC_LITERAL = re.compile(r"""["']onex\.(cmd|evt|dlq)\.[^"'\s]+["']""")

_TOPIC_ENV_VAR = re.compile(
    r"""^\s*(?:export\s+|ENV\s+)?[A-Z][A-Z0-9_]*_TOPIC\b[A-Z0-9_]*\s*=(?!=)""",
)

_LINE_SUPPRESSION_MARKERS: frozenset[str] = frozenset(
    {
        "onex-topic-sot",
        "onex-topic-test-fixture",
        "onex-topic-doc-example",
        "onex-topic-allow:",
    }
)

_RULE_TOPIC_LITERAL = "hardcoded_topic_literal"
_RULE_TOPIC_ENV_VAR = "hardcoded_topic_env_var"
_RULE_HOST_LIST = "hardcoded_host_list"


class ValidatorHardcodedTopics(ValidatorBase):
    """Reject hardcoded ONEX topic strings outside approved constant files.

    Detects ``onex.(cmd|evt|dlq).*`` quoted literals and ``*_TOPIC``
    environment-variable assignments.  Contract YAML files, topic enum
    modules, and lines with suppression markers are exempt.
    """

    validator_id: ClassVar[str] = "hardcoded_topics"

    def _is_excluded(self, path: Path) -> bool:
        if any(part in _EXCLUDED_PATH_PARTS for part in path.parts):
            return True
        return super()._is_excluded(path)

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        issues: list[ModelValidationIssue] = []

        issues.extend(self._host_list_issues(path, contract))
        if self._is_approved_file(path):
            return tuple(issues)

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return tuple(issues)

        lines = text.splitlines()
        for lineno, line in enumerate(lines, start=1):
            if self._line_is_suppressed(line):
                continue

            for match in _ONEX_TOPIC_LITERAL.finditer(line):
                enabled, severity = self._get_rule_config(_RULE_TOPIC_LITERAL, contract)
                if not enabled:
                    continue
                issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=(
                            f"hardcoded topic string {match.group()!r}"
                            " -- use a constant from the canonical topic registry"
                        ),
                        code=_RULE_TOPIC_LITERAL,
                        file_path=path,
                        line_number=lineno,
                        column_number=match.start() + 1,
                        rule_name=_RULE_TOPIC_LITERAL,
                    )
                )

            if line.lstrip().startswith(("#", "//")):
                continue
            env_match = _TOPIC_ENV_VAR.match(line)
            if env_match is None:
                continue
            enabled, severity = self._get_rule_config(_RULE_TOPIC_ENV_VAR, contract)
            if not enabled:
                continue
            issues.append(
                ModelValidationIssue(
                    severity=severity,
                    message=(
                        f"hardcoded topic env-var assignment: {env_match.group().strip()!r}"
                        " -- derive from contract subscriptions"
                    ),
                    code=_RULE_TOPIC_ENV_VAR,
                    file_path=path,
                    line_number=lineno,
                    rule_name=_RULE_TOPIC_ENV_VAR,
                )
            )

        return tuple(issues)

    def _host_list_issues(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> list[ModelValidationIssue]:
        enabled, severity = self._get_rule_config(_RULE_HOST_LIST, contract)
        rule = next((r for r in contract.rules if r.rule_id == _RULE_HOST_LIST), None)
        if not enabled or rule is None or path.suffix != ".py":
            return []
        text = path.read_text(encoding="utf-8", errors="replace")
        return host_list_issues(
            path=path,
            text=text,
            rule=rule,
            severity=severity,
            is_suppressed=self._line_is_suppressed,
        )

    @staticmethod
    def _is_approved_file(path: Path) -> bool:
        name = path.name
        if name in _APPROVED_BASENAMES:
            return True
        posix = path.as_posix()
        for suffix in _APPROVED_SUFFIXES:
            if posix.endswith(suffix):
                return True
        return False

    @staticmethod
    def _line_is_suppressed(line: str) -> bool:
        stripped = line.lstrip()
        if stripped.startswith(("#", "//")):
            for marker in _LINE_SUPPRESSION_MARKERS:
                if marker in stripped:
                    return True
        for marker in _LINE_SUPPRESSION_MARKERS:
            if marker in line:
                return True
        return False


if __name__ == "__main__":
    sys.exit(ValidatorHardcodedTopics.main())
