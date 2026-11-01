# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Replay adapter for K3 ``handler_shape``: one module's facts into ``check_handler_shape``."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.validation.checker_handler_shape import check_handler_shape
from omnibase_core.validation.validator_handler_shape import module_facts
from tests.fixtures.andon_replay.driver import ReplayContract, ReplayRun, in_scope


def _judge(
    contract: ReplayContract, path: str, text: str
) -> Sequence[ModelValidationIssue]:
    """The production validator's ``_validate_file`` body: parse the module, check it."""
    if not in_scope(contract, path):
        return ()
    try:
        facts = module_facts(path, text)
    except SyntaxError:
        return ()
    return check_handler_shape(facts, contract.subcontract.rules)


def replay(run: ReplayRun) -> Sequence[ModelValidationIssue]:
    source = run.source
    text = source.text(source.path)
    if text is None or run.contract is None:
        return ()
    return _judge(run.contract, source.path, text)


def replay_fixture(
    contract: ReplayContract, fixture: Path
) -> Sequence[ModelValidationIssue]:
    """One violation fixture: a module staged under a ``handler_*.py`` name, the file
    shape the contract's scan set and rows address."""
    return _judge(
        contract, f"handler_{fixture.name}", fixture.read_text(encoding="utf-8")
    )
