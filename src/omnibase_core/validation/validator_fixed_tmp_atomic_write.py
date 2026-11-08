# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorFixedTmpAtomicWrite -- ``fixed_tmp_atomic_write`` entry (OMN-23188).

The ``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_fixed_tmp_atomic_write`: the shared
``ValidatorBaselinedDetector`` reads one module and holds it to its entry in a shrink-only baseline
(``--baseline FILE``, one per consuming repository); this class names the pure checker. The scope and
every rule value live in ``contracts/fixed_tmp_atomic_write.validation.yaml``.

Usage (pre-commit hook ``no-fixed-tmp-atomic-write``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_fixed_tmp_atomic_write:ValidatorFixedTmpAtomicWrite --baseline .onex_ratchets/fixed_tmp_atomic_write_baseline.yaml <files...>
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_fixed_tmp_atomic_write import (
    check_fixed_tmp_atomic_write,
)
from omnibase_core.validation.validator_baselined_detector import (
    ValidatorBaselinedDetector,
)

__all__ = ["ValidatorFixedTmpAtomicWrite"]


class ValidatorFixedTmpAtomicWrite(ValidatorBaselinedDetector):
    """Read one module and judge it against the ``fixed_tmp_atomic_write`` rule row and its baseline entry."""

    validator_id: ClassVar[str] = "fixed_tmp_atomic_write"

    def _judge(
        self, path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        return check_fixed_tmp_atomic_write(path, source, rules)
