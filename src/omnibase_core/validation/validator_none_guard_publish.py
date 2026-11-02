# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorNoneGuardPublish -- ``none_guard_publish`` entry (OMN-22005, plan task T2.4).

The ``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_none_guard_publish`: the shared
``ValidatorBaselinedDetector`` reads one module and holds it to its entry in
``.onex_ratchets/none_guard_publish_baseline.yaml``; this class names the pure checker. The scope and every
rule value live in ``contracts/none_guard_publish.validation.yaml``.

Usage (pre-commit hook ``no-none-guard-publish``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_none_guard_publish:ValidatorNoneGuardPublish --baseline .onex_ratchets/none_guard_publish_baseline.yaml <files...>
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_none_guard_publish import check_none_guard_publish
from omnibase_core.validation.validator_baselined_detector import (
    ValidatorBaselinedDetector,
)

__all__ = ["ValidatorNoneGuardPublish"]


class ValidatorNoneGuardPublish(ValidatorBaselinedDetector):
    """Read one module and judge it against the ``none_guard_publish`` rule row and its baseline entry."""

    validator_id: ClassVar[str] = "none_guard_publish"

    def _judge(
        self, path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        return check_none_guard_publish(path, source, rules)
