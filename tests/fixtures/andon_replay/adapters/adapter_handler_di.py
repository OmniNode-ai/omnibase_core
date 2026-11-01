# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Replay adapter for K1 ``handler_di``: one module's facts into ``check_module``."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_handler_di_module_fact import (
    ModelHandlerDiModuleFact,
)
from omnibase_core.validation.checker_handler_di import check_module
from tests.fixtures.andon_replay.driver import ReplayContract, ReplayRun, in_scope


def replay(run: ReplayRun) -> Sequence[ModelValidationIssue]:
    source = run.source
    text = source.text(source.path)
    if text is None or run.contract is None or not in_scope(run.contract, source.path):
        return ()
    return check_module(ModelHandlerDiModuleFact(source.path, text), run.contract.rules)


def replay_fixture(
    contract: ReplayContract, fixture: Path
) -> Sequence[ModelValidationIssue]:
    """One violation fixture of the checker: a directory holding the module under judgement."""
    issues: list[ModelValidationIssue] = []
    for module in sorted(fixture.rglob("*.py")):
        relative = module.relative_to(fixture).as_posix()
        if in_scope(contract, relative):
            issues.extend(
                check_module(
                    ModelHandlerDiModuleFact(
                        relative, module.read_text(encoding="utf-8")
                    ),
                    contract.rules,
                )
            )
    return issues
