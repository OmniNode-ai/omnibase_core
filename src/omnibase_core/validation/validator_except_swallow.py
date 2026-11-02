# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorExceptSwallow -- ``except_swallow`` entry (OMN-22005, plan task T2.4).

The ``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_except_swallow`: the shared
``ValidatorBaselinedDetector`` reads one module and holds it to its entry in
``.onex_ratchets/except_swallow_baseline.yaml``; this class names the pure checker. The scope and every
rule value live in ``contracts/except_swallow.validation.yaml``.

Usage (pre-commit hook ``no-except-swallow``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_except_swallow:ValidatorExceptSwallow --baseline .onex_ratchets/except_swallow_baseline.yaml <files...>
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_except_swallow import check_except_swallow
from omnibase_core.validation.validator_baselined_detector import (
    ValidatorBaselinedDetector,
)

__all__ = ["ValidatorExceptSwallow"]


class ValidatorExceptSwallow(ValidatorBaselinedDetector):
    """Read one module and judge it against the ``except_swallow`` rule row and its baseline entry."""

    validator_id: ClassVar[str] = "except_swallow"

    def _judge(
        self, path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        return check_except_swallow(path, source, rules)
