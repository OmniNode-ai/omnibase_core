# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Replay adapter for K12 ``task_criteria``: one document, or one task of a plan, into the checker.

The production validator reads a document and calls ``check_task_criteria`` with its path as the
source name, the whole text and the contract; each rule row's own source pattern then selects the
documents it judges. The replay builds the same input:

* a plan, ticket or brief read at a revision (a code input with a line) is cut to the task block
  that holds the line, using the checker's own ``task_blocks`` split, because the audit names one
  task; a line before the first task heading selects the text before it;
* a text snapshot is judged whole, under the name of the document it was copied from (the
  snapshot's recorded provenance), or under a ticket payload name when it is a ticket description.

The production validator passes no repository lifecycle, and neither does the replay.
"""

from __future__ import annotations

import functools
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.task_criteria.model_task_criteria_check_input import (
    ModelTaskCriteriaCheckInput,
)
from omnibase_core.models.task_criteria.model_task_criteria_rules import (
    ModelTaskCriteriaRules,
)
from omnibase_core.validation.checker_task_criteria import (
    check_task_criteria,
    task_blocks,
)
from tests.fixtures.andon_replay.driver import (
    DEFAULT_CORPUS_PATH,
    ReplayContract,
    ReplayRun,
    load_corpus,
)

_TICKET = "ticket"
# A brief or a job.json spec reaches the production validator as the spec of a dispatched job,
# whose document name is ``job.json``; a reconstructed brief file name is not what it judges.
_DISPATCHED_KINDS = frozenset({"job.json", "brief"})
_DISPATCHED_NAME = "job.json"
# Repository lifecycle facts the violation fixtures are written against (the unit tests' facts).
_FIXTURE_LIFECYCLE = {"frozen_tooling": "no-code", "fixing_tooling": "fix-only"}
_ANCHORED_PREFIX = re.compile(r"\^([A-Za-z][\w-]*:)")


@functools.cache
def _snapshots() -> dict[str, tuple[str, Mapping[str, Any]]]:
    """Snapshot path -> (snapshot id, provenance), from the corpus the replay runs."""
    corpus = load_corpus(DEFAULT_CORPUS_PATH)
    return {s.path: (s.id, s.provenance) for s in corpus.snapshots}


def _ticket_prefix(contract: ModelValidatorSubcontract) -> str | None:
    """The anchored name prefix a rule's source pattern selects ticket payloads by."""
    for rule in contract.rules:
        pattern = (rule.parameters or {}).get("source_pattern")
        found = _ANCHORED_PREFIX.search(pattern) if isinstance(pattern, str) else None
        if found:
            return found.group(1)
    return None


def _document_name(path: str, contract: ModelValidatorSubcontract) -> str:
    known = _snapshots().get(path)
    if known is None:
        return path
    snapshot_id, provenance = known
    prefix = _ticket_prefix(contract)
    if prefix and (_TICKET in provenance or _TICKET in str(provenance.get("kind", ""))):
        return f"{prefix}{provenance.get(_TICKET, snapshot_id)}"
    if provenance.get("kind") in _DISPATCHED_KINDS:
        return _DISPATCHED_NAME
    recorded = provenance.get("source")
    return recorded if isinstance(recorded, str) else path


def _task_text(text: str, name: str, rules: ModelTaskCriteriaRules, line: int) -> str:
    """The task block holding 1-based ``line``; the text before the first heading if above it."""
    blocks = task_blocks(text, name, rules)
    if len(blocks) == 1 and blocks[0] == (name, text):
        return text
    lines = text.splitlines()
    sizes = [block.count("\n") + 1 for _, block in blocks]
    begin = len(lines) - sum(sizes)
    if line <= begin:
        return "\n".join(lines[:begin])
    for (_, block), size in zip(blocks, sizes, strict=True):
        if line <= begin + size:
            return block
        begin += size
    return text


def _judge(
    name: str,
    text: str,
    contract: ModelValidatorSubcontract,
    lifecycle: Mapping[str, str] | None = None,
) -> tuple[ModelValidationIssue, ...]:
    result = check_task_criteria(
        ModelTaskCriteriaCheckInput(
            source_name=name,
            text=text,
            contract=contract,
            repository_lifecycle=dict(lifecycle or {}),
        )
    )
    return tuple(i.model_copy(update={"file_path": Path(name)}) for i in result.issues)


def replay(run: ReplayRun) -> Sequence[ModelValidationIssue]:
    source = run.source
    if run.contract is None:
        return ()
    contract = run.contract.subcontract
    text = source.text(source.path)
    if text is None:
        return ()
    name = _document_name(source.path, contract)
    if source.line is not None:
        text = _task_text(
            text, name, ModelTaskCriteriaRules.from_contract(contract), source.line
        )
    return _judge(name, text, contract)


def _fixture_names(contract: ModelValidatorSubcontract, rule_id: str) -> list[str]:
    """Document names the fixture's rule judges, one per kind the contract scans.

    The names are built from the contract's own target patterns and ticket prefix; when the
    fixture's rule row is known only the names its source pattern selects are kept.
    """
    names = [p.removeprefix("**/").replace("*", "x") for p in contract.target_patterns]
    prefix = _ticket_prefix(contract)
    if prefix:
        names.append(f"{prefix}x")
    row = ModelTaskCriteriaRules.from_contract(contract).rows.get(rule_id)
    return names if row is None else [n for n in names if row.judges(n)]


def replay_fixture(
    contract: ReplayContract, fixture: Path
) -> Sequence[ModelValidationIssue]:
    """One violation fixture ``<kind>_<rule id>.<ext>``: its text, judged as the rule's document."""
    text = fixture.read_text(encoding="utf-8")
    rule_id = fixture.stem.partition("_")[2]
    issues: dict[tuple[str | None, str], ModelValidationIssue] = {}
    for name in _fixture_names(contract.subcontract, rule_id):
        for issue in _judge(name, text, contract.subcontract, _FIXTURE_LIFECYCLE):
            issues.setdefault((issue.code, issue.message), issue)
    return list(issues.values())
