# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Replay adapter for K10 ``checker_rule_data``: one module and the names beside it into ``check_module``.

The module fact is built the way ``ValidatorCheckerRuleData`` builds it. The replay runs the
validator as the hook's default (no baseline, no base revision), so a module is new in the change.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_checker_rule_data_module_fact import (
    ModelCheckerRuleDataModuleFact,
)
from omnibase_core.validation.checker_checker_rule_data import check_module
from tests.fixtures.andon_replay.driver import ReplayContract, ReplayRun, in_scope

_CONTRACTS_DIR = "contracts"


def _names_in(names: Sequence[str], directory: PurePosixPath) -> frozenset[str]:
    """The entries directly inside ``directory``: files and the first part of deeper paths."""
    return frozenset(
        PurePosixPath(name).relative_to(directory).parts[0]
        for name in names
        if directory in PurePosixPath(name).parents
    )


def _judge(
    contract: ReplayContract, path: str, source: str, names: Sequence[str]
) -> Sequence[ModelValidationIssue]:
    located = PurePosixPath(path)
    fact = ModelCheckerRuleDataModuleFact(
        name=located.name,
        posix_path=path,
        source=source,
        sibling_names=_names_in(names, located.parent),
        contract_names=_names_in(names, located.parent / _CONTRACTS_DIR),
    )
    return check_module(Path(path), fact, contract.rules)


def replay(run: ReplayRun) -> Sequence[ModelValidationIssue]:
    source = run.source
    text = source.text(source.path)
    if text is None or run.contract is None or not in_scope(run.contract, source.path):
        return ()
    return _judge(run.contract, source.path, text, source.names())


def replay_fixture(
    contract: ReplayContract, fixture: Path
) -> Sequence[ModelValidationIssue]:
    """One violation fixture: a directory holding the module under judgement."""
    names = sorted(
        p.relative_to(fixture).as_posix() for p in fixture.rglob("*") if p.is_file()
    )
    issues: list[ModelValidationIssue] = []
    for name in names:
        if name.endswith(".py") and in_scope(contract, name):
            body = (fixture / name).read_text(encoding="utf-8", errors="replace")
            issues.extend(_judge(contract, name, body, names))
    return issues
