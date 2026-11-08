# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorTimeBoundTruncation -- ``time_bound_truncation`` entry (OMN-23186).

The ``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_time_bound_truncation`: the shared
``ValidatorBaselinedDetector`` reads one module and holds it to its entry in
``.onex_ratchets/time_bound_truncation_baseline.yaml``; this class names the pure checker. The scope and every
rule value live in ``contracts/time_bound_truncation.validation.yaml``.

Usage (pre-commit hook ``no-time-bound-truncation``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_time_bound_truncation:ValidatorTimeBoundTruncation --baseline .onex_ratchets/time_bound_truncation_baseline.yaml <files...>
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_time_bound_truncation import (
    check_time_bound_truncation,
)
from omnibase_core.validation.validator_baselined_detector import (
    ValidatorBaselinedDetector,
)

__all__ = ["ValidatorTimeBoundTruncation"]


class ValidatorTimeBoundTruncation(ValidatorBaselinedDetector):
    """Read one module and judge it against the ``time_bound_truncation`` rule row and its baseline entry."""

    validator_id: ClassVar[str] = "time_bound_truncation"

    def _judge(
        self, path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        return check_time_bound_truncation(path, source, rules)
