# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorIdFromStamp -- ``id_from_stamp`` entry (OMN-23189, gate OMN-21433 AC-4).

The ``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_id_from_stamp`: the shared
``ValidatorBaselinedDetector`` reads one module and holds it to its entry in
``.onex_ratchets/id_from_stamp_baseline.yaml``; this class names the pure checker. The scope and every
rule value live in ``contracts/id_from_stamp.validation.yaml``.

Usage (pre-commit hook ``no-id-from-stamp``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_id_from_stamp:ValidatorIdFromStamp --baseline .onex_ratchets/id_from_stamp_baseline.yaml <files...>
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_id_from_stamp import check_id_from_stamp
from omnibase_core.validation.validator_baselined_detector import (
    ValidatorBaselinedDetector,
)

__all__ = ["ValidatorIdFromStamp"]


class ValidatorIdFromStamp(ValidatorBaselinedDetector):
    """Read one module and judge it against the ``id_from_stamp`` rule row and its baseline entry."""

    validator_id: ClassVar[str] = "id_from_stamp"

    def _judge(
        self, path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        return check_id_from_stamp(path, source, rules)
