# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Replay adapter for K9 ``inline_logic``: one workflow or ticket contract into ``check_inline_logic``."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.inline_logic.model_inline_logic_document import (
    ModelInlineLogicDocument,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model
from omnibase_core.validation.checker_inline_logic import check_inline_logic
from tests.fixtures.andon_replay.driver import ReplayContract, ReplayRun, in_scope


def _judge(
    contract: ReplayContract, path: str, text: str
) -> Sequence[ModelValidationIssue]:
    """The production validator's read of one file: parse it, hand its steps and values over."""
    document = load_yaml_content_as_model(text, ModelInlineLogicDocument)
    return check_inline_logic(
        Path(path),
        document.run_steps,
        document.check_values,
        contract.subcontract.rules,
    )


def _scoped(contract: ReplayContract, path: str) -> bool:
    """The contract's scan set for a repository-relative path.

    The production scan expands each target pattern as a glob under the repository root,
    so a pattern written without a leading wildcard names a path from the root; the
    driver's scope test roots the path, so the root-relative spelling is offered too.
    """
    sub = contract.subcontract
    rooted = sub.model_copy(
        update={
            "target_patterns": [
                *sub.target_patterns,
                *(f"/{pattern}" for pattern in sub.target_patterns),
            ]
        }
    )
    return in_scope(replace(contract, subcontract=rooted), path)


def replay(run: ReplayRun) -> Sequence[ModelValidationIssue]:
    source = run.source
    text = source.text(source.path)
    if text is None or run.contract is None or not _scoped(run.contract, source.path):
        return ()
    return _judge(run.contract, source.path, text)


def replay_fixture(
    contract: ReplayContract, fixture: Path
) -> Sequence[ModelValidationIssue]:
    """One violation fixture: a single workflow or contract file, judged without the scan scope."""
    return _judge(contract, fixture.name, fixture.read_text(encoding="utf-8"))
