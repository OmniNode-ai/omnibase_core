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

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.validator_base import ValidatorBase

_ONEX_TOPIC_LITERAL = re.compile(r"""["']onex\.(cmd|evt|dlq)\.[a-z0-9._-]+\.v\d+["']""")

_TOPIC_ENV_VAR = re.compile(
    r"""^[A-Z_]*(?:INPUT|OUTPUT|_)_?TOPIC\b[A-Z_]*\s*[:=]""",
    re.MULTILINE,
)

_LINE_SUPPRESSION_MARKERS: frozenset[str] = frozenset(
    {
        "onex-topic-sot",
        "onex-topic-test-fixture",
        "onex-topic-doc-example",
        "onex-topic-allow:",
    }
)

_APPROVED_BASENAMES: frozenset[str] = frozenset(
    {
        "topics.py",
        "topics.ts",
        "topics.yaml",
        "topic_constants.py",
        "constants_topic_taxonomy.py",
        "platform_topic_suffixes.py",
        "topic_naming_baseline.txt",
        "governance_emitter.py",
        "contract_topic_extractor.py",
        "check_topic_drift.py",
    }
)

_APPROVED_SUFFIXES: frozenset[str] = frozenset(
    {
        "/contract.yaml",
        "/handler_contract.yaml",
    }
)

_RULE_TOPIC_LITERAL = "hardcoded_topic_literal"
_RULE_TOPIC_ENV_VAR = "hardcoded_topic_env_var"


class ValidatorHardcodedTopics(ValidatorBase):
    """Reject hardcoded ONEX topic strings outside approved constant files.

    Detects ``onex.(cmd|evt|dlq).*`` quoted literals and ``*_TOPIC``
    environment-variable assignments.  Contract YAML files, topic enum
    modules, and lines with suppression markers are exempt.
    """

    validator_id: ClassVar[str] = "hardcoded_topics"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        issues: list[ModelValidationIssue] = []

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

        stripped = text.lstrip()
        if stripped and not stripped.startswith(("#", "---", "contract_kind:")):
            for match in _TOPIC_ENV_VAR.finditer(text):
                matched_line = text[: match.start()].count("\n") + 1
                if matched_line > len(lines):
                    continue
                line_text = lines[matched_line - 1]
                if self._line_is_suppressed(line_text):
                    continue
                enabled, severity = self._get_rule_config(_RULE_TOPIC_ENV_VAR, contract)
                if not enabled:
                    continue
                issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=(
                            f"hardcoded topic env-var assignment: {match.group().strip()!r}"
                            " -- derive from contract subscriptions"
                        ),
                        code=_RULE_TOPIC_ENV_VAR,
                        file_path=path,
                        line_number=matched_line,
                        rule_name=_RULE_TOPIC_ENV_VAR,
                    )
                )

        return tuple(issues)

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
