# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorHardcodedModelLiterals -- the generic-format entry for K6 families O, G, F, P, S, H and B (OMN-21537).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_hardcoded_model_literals`:
it loads ``contracts/hardcoded_model_literals.validation.yaml`` as the validator contract,
reads each file and hands its path and text to the pure checker. The three repository
facts (organisation, registry repositories, lab hosts) are constructor arguments; a
validator built without them judges O, S and B, and F, and leaves G, P and H inert.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from importlib import resources
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_hardcoded_literal_rule_set import (
    ModelHardcodedLiteralRuleSet,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model
from omnibase_core.validation.checker_hardcoded_model_literals import (
    check_text,
    load_rule_set,
)
from omnibase_core.validation.hardcoded_model_config.models import (
    ModelHardcodedModelConfigPolicy,
)
from omnibase_core.validation.validator_base import ValidatorBase


def _packaged_policy() -> ModelHardcodedModelConfigPolicy:
    """The policy shipped in the scanner package: the text forms the checker reads."""
    package = resources.files("omnibase_core.validation.hardcoded_model_config")
    return load_yaml_content_as_model(
        package.joinpath("policy.yaml").read_text("utf-8"),
        ModelHardcodedModelConfigPolicy,
    )


class ValidatorHardcodedModelLiterals(ValidatorBase):
    """Refuse operational numbers, first-party URLs, locations, lists, stamps and budgets in code."""

    validator_id: ClassVar[str] = "hardcoded_model_literals"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        github_org: str = "",
        repository_names: Iterable[str] = (),
        host_names: Iterable[str] = (),
        text_forms: ModelHardcodedModelConfigPolicy | None = None,
    ) -> None:
        super().__init__(contract)
        forms = text_forms or _packaged_policy()
        self._rule_set: ModelHardcodedLiteralRuleSet = load_rule_set(
            self.contract.rules,
            github_org=github_org,
            repository_names=repository_names,
            host_names=host_names,
            python_suffixes=forms.python_suffixes,
            slash_comment_suffixes=forms.slash_comment_suffixes,
            no_comment_suffixes=forms.no_comment_suffixes,
            exclude_patterns=self.contract.exclude_patterns,
        )

    @property
    def rule_set(self) -> ModelHardcodedLiteralRuleSet:
        """The rule rows and facts this validator judges with."""
        return self._rule_set

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        text = path.read_text(encoding="utf-8", errors="replace")
        return check_text(path.as_posix(), text, self._rule_set)


if __name__ == "__main__":
    sys.exit(ValidatorHardcodedModelLiterals.main())
