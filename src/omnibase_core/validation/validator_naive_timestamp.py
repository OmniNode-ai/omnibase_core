# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorNaiveTimestamp -- ``naive_timestamp`` entry (OMN-23186).

The ``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_naive_timestamp`: the shared
``ValidatorBaselinedDetector`` reads one module and holds it to its entry in
``.onex_ratchets/naive_timestamp_baseline.yaml``; this class names the pure checker. The scope and every
rule value live in ``contracts/naive_timestamp.validation.yaml``.

Usage (pre-commit hook ``no-naive-timestamp``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_naive_timestamp:ValidatorNaiveTimestamp --baseline .onex_ratchets/naive_timestamp_baseline.yaml <files...>
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_naive_timestamp import (
    check_naive_timestamp,
)
from omnibase_core.validation.validator_baselined_detector import (
    ValidatorBaselinedDetector,
)

__all__ = ["ValidatorNaiveTimestamp"]


class ValidatorNaiveTimestamp(ValidatorBaselinedDetector):
    """Read one module and judge it against the ``naive_timestamp`` rule row and its baseline entry."""

    validator_id: ClassVar[str] = "naive_timestamp"

    def _judge(
        self, path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        return check_naive_timestamp(path, source, rules)
