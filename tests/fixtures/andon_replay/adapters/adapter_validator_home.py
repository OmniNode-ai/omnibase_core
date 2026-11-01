# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Replay adapter for K7 ``validator_home``: one hook config, node contract or test file into the checker.

The facts are built the way ``ValidatorValidatorHome`` builds them from a path, read here
from the audited revision (or a fixture tree) instead of the working tree. A hook config
holds many hooks and the checker reports one issue per offending hook, so the hooks handed
over are those whose block holds the audited line, when the assertion names one.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath

import yaml

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.validation.model_validator_home_contract_fact import (
    ModelValidatorHomeContractFact,
)
from omnibase_core.models.validation.model_validator_home_hook_fact import (
    ModelValidatorHomeHookFact,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_rule_parameters import rule_strings
from omnibase_core.validation.checker_validator_home import (
    RULE_LOCAL_HOOK,
    RULE_NODE,
    RULE_PINNING_TEST,
    RULE_PYTEST_HOOK,
    RULE_SCRIPT_HOOK,
    check_hooks,
    check_node,
    check_test_file,
)
from tests.fixtures.andon_replay.driver import ReplayContract, ReplayRun, in_scope

type TextOf = Callable[[str], str | None]
type NamesOf = Callable[[], list[str]]


def _matches(
    rules: dict[str, ModelValidatorRule],
    rule_ids: tuple[str, ...],
    key: str,
    path: str,
) -> bool:
    return any(
        re.search(pattern, path)
        for rule_id in rule_ids
        if rule_id in rules and rules[rule_id].enabled
        for pattern in rule_strings(rules[rule_id], key)
    )


def _hook_spans(text: str) -> list[tuple[int, int]]:
    """First and last line (1-based, inclusive) of each hook mapping, in the order the facts list them."""
    spans: list[tuple[int, int]] = []
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    if not isinstance(root, yaml.MappingNode):
        return spans
    for key, repos in root.value:
        if key.value != "repos" or not isinstance(repos, yaml.SequenceNode):
            continue
        for repo in repos.value:
            if not isinstance(repo, yaml.MappingNode):
                continue
            for repo_key, hooks in repo.value:
                if repo_key.value != "hooks" or not isinstance(
                    hooks, yaml.SequenceNode
                ):
                    continue
                spans.extend(
                    (
                        hook.start_mark.line + 1,
                        max(hook.end_mark.line, hook.start_mark.line + 1),
                    )
                    for hook in hooks.value
                    if isinstance(hook, yaml.MappingNode)
                )
    return spans


def _hook_facts(
    path: str, text: str, line: int | None
) -> tuple[ModelValidatorHomeHookFact, ...]:
    data = load_yaml_mapping_no_duplicates(text, source=path)
    repos = data.get("repos", [])
    hooks: list[ModelValidatorHomeHookFact] = []
    for repo in repos if isinstance(repos, list) else []:
        if not isinstance(repo, dict):
            continue
        for hook in repo.get("hooks", []) or []:
            if isinstance(hook, dict):
                hooks.append(
                    ModelValidatorHomeHookFact(
                        hook_id=str(hook.get("id", "")),
                        repo=str(repo.get("repo", "")),
                        language=str(hook.get("language", "")),
                        entry=str(hook.get("entry", "")),
                    )
                )
    if line is None:
        return tuple(hooks)
    spans = _hook_spans(text)
    if len(spans) != len(hooks):
        return tuple(hooks)
    return tuple(
        hook
        for hook, (first, last) in zip(hooks, spans, strict=True)
        if first <= line <= last
    )


def _node_fact(
    path: str, text: str, text_of: TextOf, names: NamesOf
) -> ModelValidatorHomeContractFact:
    data = load_yaml_mapping_no_duplicates(text, source=path)
    output = data.get("output_model", "")
    if isinstance(output, dict):
        output = output.get("name", "")
    directory = PurePosixPath(path).parent
    sources = tuple(
        body
        for name in sorted(names())
        if PurePosixPath(name).suffix == ".py"
        and directory in PurePosixPath(name).parents
        and (body := text_of(name)) is not None
    )
    return ModelValidatorHomeContractFact(
        directory_name=directory.name,
        contract_name=str(data.get("name", "")),
        output_model=str(output),
        handler_sources=sources,
    )


def _judge(
    contract: ReplayContract,
    path: str,
    line: int | None,
    text_of: TextOf,
    names: NamesOf,
) -> Sequence[ModelValidationIssue]:
    text = text_of(path)
    if text is None:
        return ()
    rules = contract.rules
    located = Path(path)
    if _matches(
        rules,
        (RULE_LOCAL_HOOK, RULE_SCRIPT_HOOK, RULE_PYTEST_HOOK),
        "config_name_patterns",
        path,
    ):
        return check_hooks(located, _hook_facts(path, text, line), rules)
    if _matches(rules, (RULE_NODE,), "contract_name_patterns", path):
        return check_node(located, _node_fact(path, text, text_of, names), rules)
    if _matches(rules, (RULE_PINNING_TEST,), "test_name_patterns", path):
        return check_test_file(located, text, rules)
    return ()


def replay(run: ReplayRun) -> Sequence[ModelValidationIssue]:
    source = run.source
    if run.contract is None or not in_scope(run.contract, source.path):
        return ()
    return _judge(run.contract, source.path, source.line, source.text, source.names)


def replay_fixture(
    contract: ReplayContract, fixture: Path
) -> Sequence[ModelValidationIssue]:
    """One violation fixture: a file, or a directory holding a node with its handlers."""
    root = fixture if fixture.is_dir() else fixture.parent

    def text_of(path: str) -> str | None:
        target = root / path
        return (
            target.read_text(encoding="utf-8", errors="replace")
            if target.is_file()
            else None
        )

    def names() -> list[str]:
        return sorted(
            p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
        )

    paths = (
        [
            p.relative_to(root).as_posix()
            for p in sorted(fixture.rglob("*"))
            if p.is_file()
        ]
        if fixture.is_dir()
        else [fixture.name]
    )
    issues: list[ModelValidationIssue] = []
    for path in paths:
        issues.extend(_judge(contract, path, None, text_of, names))
    return issues
