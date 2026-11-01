# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Replay adapter for ``first_party_ref``: the audited file (and its comparison file) into the checker.

The production validator gathers the files the contract's target patterns select, labelled by
repository-relative path, and hands them to ``check_first_party_refs`` in path order. The replay
does the same with the audited file and the file the assertion's ``comparison_file`` fact names
(the other home in a single-home finding). The fact's path is not part of the replay source, so
the comparison file is labelled by the tree name, in scope of the contract, whose content at the
audited revision is the fact's content. No tag inventory is gathered (that is the runtime's network
effect), so a sibling pin in a ``pyproject.toml`` is judged against an empty inventory.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_first_party_ref_input import (
    ModelFirstPartyRefInput,
)
from omnibase_core.validation.checker_first_party_ref import (
    check_first_party_refs,
    matches,
)
from tests.fixtures.andon_replay.driver import ReplayContract, ReplayRun, ReplaySource

_COMPARISON_ROLE = "comparison_file"
_JSON_SUFFIX = ".json"


def _selected(contract: ReplayContract, label: str) -> bool:
    sub = contract.subcontract
    return matches(label, sub.target_patterns) and not matches(
        label, sub.exclude_patterns
    )


def _comparison_label(source: ReplaySource, contract: ReplayContract) -> str | None:
    body = source.fact_text(_COMPARISON_ROLE)
    if body is None:
        return None
    for name in sorted(source.fact_names(_COMPARISON_ROLE)):
        if _selected(contract, name) and source.text(name) == body:
            return name
    return None


def replay(run: ReplayRun) -> Sequence[ModelValidationIssue]:
    source = run.source
    contract = run.contract
    if contract is None or not _selected(contract, source.path):
        return ()
    text = source.text(source.path)
    if text is None:
        return ()
    files = {source.path: text}
    label = _comparison_label(source, contract)
    comparison = source.fact_text(_COMPARISON_ROLE)
    if label is not None and comparison is not None:
        files.setdefault(label, comparison)
    facts = ModelFirstPartyRefInput(
        files=tuple(
            ModelSourceFile(path=path, source=body)
            for path, body in sorted(files.items())
        )
    )
    return check_first_party_refs(facts, contract.subcontract)


def replay_fixture(
    contract: ReplayContract, fixture: Path
) -> Sequence[ModelValidationIssue]:
    """One violation fixture: a facts bundle (``.json``), or a source whose bundle names its path."""
    if fixture.suffix == _JSON_SUFFIX:
        facts = ModelFirstPartyRefInput.model_validate(
            json.loads(fixture.read_text(encoding="utf-8"))
        )
    else:
        companion = fixture.with_suffix(_JSON_SUFFIX)
        if not companion.is_file():
            return ()
        base = ModelFirstPartyRefInput.model_validate(
            json.loads(companion.read_text(encoding="utf-8"))
        )
        if len(base.files) != 1:
            return ()
        named = ModelSourceFile(
            path=base.files[0].path, source=fixture.read_text(encoding="utf-8")
        )
        facts = base.model_copy(update={"files": (named,)})
    return check_first_party_refs(facts, contract.subcontract)
