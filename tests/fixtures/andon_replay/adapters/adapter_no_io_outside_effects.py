# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Replay adapter for K4 ``no_io_outside_effects``: a module and its node contract into
``check_no_io_outside_effects``."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_no_io_outside_effects_facts import (
    ModelNoIoOutsideEffectsFacts,
)
from omnibase_core.validation.checker_no_io_outside_effects import (
    RULE_SCOPE,
    check_no_io_outside_effects,
)
from omnibase_core.validation.checker_rule_parameters import rule_string
from tests.fixtures.andon_replay.driver import ReplayContract, ReplayRun, in_scope

_CONTRACT_ROLE = "node_contract"


def _judge(
    contract: ReplayContract,
    module: ModelSourceFile,
    contract_source: ModelSourceFile | None,
) -> Sequence[ModelValidationIssue]:
    if contract_source is None or not in_scope(contract, module.path):
        return ()
    return check_no_io_outside_effects(
        ModelNoIoOutsideEffectsFacts(contract=contract_source, module=module),
        contract.rules,
    )


def replay(run: ReplayRun) -> Sequence[ModelValidationIssue]:
    """The module at ``run.source.path`` judged against its node contract: the fact the
    assertion names, else the nearest contract above the module, as the validator finds it."""
    source = run.source
    if run.contract is None:
        return ()
    text = source.text(source.path)
    if text is None:
        return ()
    name = rule_string(run.contract.rules[RULE_SCOPE], "contract_filename")
    found: ModelSourceFile | None = None
    fact = source.fact_text(_CONTRACT_ROLE)
    if fact is not None:
        found = ModelSourceFile(path=name, source=fact)
    else:
        for parent in PurePosixPath(source.path).parents:
            candidate = (parent / name).as_posix()
            body = source.text(candidate)
            if body is not None:
                found = ModelSourceFile(path=candidate, source=body)
                break
    return _judge(run.contract, ModelSourceFile(path=source.path, source=text), found)


def replay_fixture(
    contract: ReplayContract, fixture: Path
) -> Sequence[ModelValidationIssue]:
    """One violation fixture: a directory holding the node contract and its modules.

    A module is judged against the nearest contract at or above it inside the fixture; a
    contract that carries a fault of its own is judged alone."""
    name = rule_string(contract.rules[RULE_SCOPE], "contract_filename")
    issues: list[ModelValidationIssue] = []
    contract_file = fixture / name
    if contract_file.is_file():
        issues.extend(
            check_no_io_outside_effects(
                ModelNoIoOutsideEffectsFacts(
                    contract=ModelSourceFile(
                        path=name, source=contract_file.read_text(encoding="utf-8")
                    )
                ),
                contract.rules,
            )
        )
    for module in sorted(fixture.rglob("*.py")):
        relative = module.relative_to(fixture).as_posix()
        for parent in module.relative_to(fixture).parents:
            candidate = fixture / parent / name
            if candidate.is_file():
                issues.extend(
                    _judge(
                        contract,
                        ModelSourceFile(
                            path=relative,
                            source=module.read_text(encoding="utf-8"),
                        ),
                        ModelSourceFile(
                            path=(parent / name).as_posix(),
                            source=candidate.read_text(encoding="utf-8"),
                        ),
                    )
                )
                break
    return issues
