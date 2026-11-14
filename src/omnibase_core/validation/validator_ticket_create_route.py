# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorTicketCreateRoute -- ``ticket_create_route`` entry (OMN-23770).

The ``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_ticket_create_route`. The
contract carries no ``baseline_ratchet`` row, so no baseline is read and every site is a finding; the
scope and every rule value live in ``contracts/ticket_create_route.validation.yaml``.

Usage (pre-commit hook ``no-direct-ticket-create``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_ticket_create_route:ValidatorTicketCreateRoute <files...>
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_ticket_create_route import (
    check_ticket_create_route,
)
from omnibase_core.validation.validator_baselined_detector import (
    ValidatorBaselinedDetector,
)

__all__ = ["ValidatorTicketCreateRoute"]


class ValidatorTicketCreateRoute(ValidatorBaselinedDetector):
    """Read one module and judge it against the ``ticket_create_route`` rule row, with no baseline."""

    validator_id: ClassVar[str] = "ticket_create_route"

    def _judge(
        self, path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        return check_ticket_create_route(path, source, rules)
