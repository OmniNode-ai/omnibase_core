# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Merge-key sequence precedence must not depend on the installed PyYAML.

PyYAML 6.0.3 resolves ``<<: [*first, *second]`` so that the first mapping wins
(the YAML merge-key rule); 6.0.4 lets the last mapping win. The handler resolves
the merge itself, so these cases hold on both versions.

The autouse fixture swaps in both precedence rules for ``SafeConstructor``, so each
case is checked against the first-wins and the last-wins constructor whichever
PyYAML is installed.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
import yaml
from yaml.constructor import ConstructorError, SafeConstructor
from yaml.nodes import MappingNode, SequenceNode

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.precommit_interpreter_check.model_precommit_interpreter_check_input import (
    ModelPrecommitInterpreterCheckInput,
)
from omnibase_core.nodes.node_precommit_interpreter_check_compute.handler import (
    NodePrecommitInterpreterCheckCompute,
)
from omnibase_core.nodes.node_precommit_interpreter_check_compute.matcher_precommit_interpreter import (
    eligible_entries,
)

pytestmark = pytest.mark.unit

_BARE = "python x.py"
_WRAPPED = "uv run python x.py"
_PADDING = "".join(
    f"      - id: pad-{index}\n        entry: {_WRAPPED}\n" for index in range(10)
)


def _flatten_mapping_with(*, first_wins: bool) -> Callable[..., None]:
    """Build a ``SafeConstructor.flatten_mapping`` with the chosen merge precedence."""

    def flatten_mapping(self: SafeConstructor, node: MappingNode) -> None:
        merge: list[tuple[object, object]] = []
        index = 0
        while index < len(node.value):
            key_node, value_node = node.value[index]
            if key_node.tag == "tag:yaml.org,2002:merge":
                del node.value[index]
                if isinstance(value_node, MappingNode):
                    flatten_mapping(self, value_node)
                    merge.extend(value_node.value)
                elif isinstance(value_node, SequenceNode):
                    submerge = []
                    for subnode in value_node.value:
                        if not isinstance(subnode, MappingNode):
                            raise ConstructorError(
                                "while constructing a mapping",
                                node.start_mark,
                                f"expected a mapping for merging, but found {subnode.id}",
                                subnode.start_mark,
                            )
                        flatten_mapping(self, subnode)
                        submerge.append(subnode.value)
                    if first_wins:
                        submerge.reverse()
                    for value in submerge:
                        merge.extend(value)
                else:
                    raise ConstructorError(
                        "while constructing a mapping",
                        node.start_mark,
                        "expected a mapping or list of mappings for merging, "
                        f"but found {value_node.id}",
                        value_node.start_mark,
                    )
            elif key_node.tag == "tag:yaml.org,2002:value":
                key_node.tag = "tag:yaml.org,2002:str"
                index += 1
            else:
                index += 1
        if merge:
            node.value = merge + node.value

    return flatten_mapping


@pytest.fixture(
    autouse=True,
    params=["installed", "pyyaml-6.0.3-first-wins", "pyyaml-6.0.4-last-wins"],
)
def pyyaml_merge_rule(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> str:
    """Run every case under the installed PyYAML and under both merge precedences."""
    rule = str(request.param)
    if rule != "installed":
        monkeypatch.setattr(
            yaml.constructor.SafeConstructor,
            "flatten_mapping",
            _flatten_mapping_with(first_wins=rule.endswith("first-wins")),
        )
    return rule


def _config(anchors: str, merged: str) -> str:
    return f"{anchors}repos:\n  - hooks:\n      - {merged}\n{_PADDING}"


_ANCHORS = (
    f"first: &first\n  id: merged-first\n  entry: {_BARE}\n"
    f"second: &second\n  entry: {_WRAPPED}\n"
)


def _messages(source: str) -> list[str]:
    report = NodePrecommitInterpreterCheckCompute().handle(
        ModelPrecommitInterpreterCheckInput(
            config=ModelSourceFile(path=".pre-commit-config.yaml", source=source),
            scripts=[],
            repository_root="/repo",
        )
    )
    return [finding.message for finding in report.findings]


def _merged_entry(source: str) -> str:
    return next(
        entry for label, entry, _ in eligible_entries(source) if label == "merged-first"
    )


def test_first_mapping_wins_for_bare_entry_first() -> None:
    source = _config(_ANCHORS, "<<: [*first, *second]")
    assert _merged_entry(source) == _BARE
    assert _messages(source) == [
        "merged-first: entry invokes bare `python` -- use `uv run python` "
        f"(macOS has no bare `python`; entry={_BARE!r})"
    ]


def test_first_mapping_wins_for_wrapped_entry_first() -> None:
    source = _config(_ANCHORS, "<<: [*second, *first]")
    assert _merged_entry(source) == _WRAPPED
    assert _messages(source) == []


def test_own_key_overrides_merge_sequence() -> None:
    source = _config(_ANCHORS, f"<<: [*first, *second]\n        entry: {_WRAPPED}")
    assert _merged_entry(source) == _WRAPPED
    assert _messages(source) == []


def test_nested_merge_inside_sequence_source_keeps_first_precedence() -> None:
    anchors = (
        f"base: &base\n  entry: {_WRAPPED}\n"
        f"first: &first\n  <<: *base\n  id: merged-first\n"
        f"second: &second\n  entry: {_BARE}\n"
    )
    source = _config(anchors, "<<: [*first, *second]")
    assert _merged_entry(source) == _WRAPPED
    assert _messages(source) == []


def test_repeated_merge_keys_later_key_wins() -> None:
    source = _config(_ANCHORS, "<<: *first\n        <<: *second")
    assert _merged_entry(source) == _WRAPPED
    assert _messages(source) == []
