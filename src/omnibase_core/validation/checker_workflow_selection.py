# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Workflow selection for the merge-queue parity CLI, read from a rule row (OMN-21503)."""

from __future__ import annotations

import re
from functools import cache
from importlib import resources

from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model
from omnibase_core.validation.checker_rule_parameters import rule_string

__all__ = ["is_workflow", "load_workflow_rule"]


@cache
def load_workflow_rule() -> ModelValidatorRule:
    """Load workflow selection data shipped with the package."""
    raw = resources.files("omnibase_core.validation").joinpath(
        "contracts/merge_queue_parity.validation.yaml"
    )
    contract = load_yaml_content_as_model(
        raw.read_text("utf-8"), ModelValidatorSubcontract
    )
    return {row.rule_id: row for row in contract.rules}["workflow_path"]


def is_workflow(path: str, *, rule: ModelValidatorRule | None = None) -> bool:
    """True for a workflow selected by the packaged rule's path pattern."""
    row = load_workflow_rule() if rule is None else rule
    return bool(re.match(rule_string(row, "path_pattern"), path))
