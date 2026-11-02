# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorImportNoneFallback -- ``import_none_fallback`` entry (OMN-22005, plan task T2.4).

The ``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_import_none_fallback`: the shared
``ValidatorBaselinedDetector`` reads one module and holds it to its entry in
``.onex_ratchets/import_none_fallback_baseline.yaml``; this class names the pure checker. The scope and every
rule value live in ``contracts/import_none_fallback.validation.yaml``.

Usage (pre-commit hook ``no-import-none-fallback``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_import_none_fallback:ValidatorImportNoneFallback --baseline .onex_ratchets/import_none_fallback_baseline.yaml <files...>
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_import_none_fallback import (
    check_import_none_fallback,
)
from omnibase_core.validation.validator_baselined_detector import (
    ValidatorBaselinedDetector,
)

__all__ = ["ValidatorImportNoneFallback"]


class ValidatorImportNoneFallback(ValidatorBaselinedDetector):
    """Read one module and judge it against the ``import_none_fallback`` rule row and its baseline entry."""

    validator_id: ClassVar[str] = "import_none_fallback"

    def _judge(
        self, path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        return check_import_none_fallback(path, source, rules)
