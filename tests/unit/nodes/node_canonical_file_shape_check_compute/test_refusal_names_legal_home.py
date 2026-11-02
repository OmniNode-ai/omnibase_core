# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A refusal of a new code file names the legal home and the move (OMN-19998).

Lanes that planted a script, a handler or a node directory in a repository that
is not omnimarket were refused with text that named the canonical locations of
the repository but not where a new node lives, so the next attempt walked into
the node-home refusal. The wording is a ``parameters`` entry of the validator
contract; these tests read it from there and run the real checkers, so a
planted file is refused with a message that carries the legal home and the move.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.nodes.node_canonical_file_shape_check_compute.matcher_node_home import (
    NodeHomeRule,
)
from tests.unit.nodes.node_canonical_file_shape_check_compute.support import (
    RULES,
    git,
    init_repo,
    issues,
    write,
)
from tests.unit.nodes.node_canonical_file_shape_check_compute.test_node_home_admission import (
    _plant,
    _request,
)

pytestmark = pytest.mark.unit

LEGAL_HOME_REPO = "omnimarket"
LEGAL_HOME_PATH = "src/omnimarket/nodes/node_<name>/"
MOVE = "move"

REFUSAL_TEXT_KEYS = (
    "noncanonical_text",
    "shell_text",
    "handler_outside_node_text",
    "node_home_outside_market_text",
)


def _assert_names_home_and_move(message: str) -> None:
    assert LEGAL_HOME_REPO in message
    assert LEGAL_HOME_PATH in message
    assert MOVE in message.lower()


@pytest.mark.parametrize("key", REFUSAL_TEXT_KEYS)
def test_each_refusal_text_in_the_contract_names_the_legal_home_and_the_move(
    key: str,
) -> None:
    _assert_names_home_and_move(getattr(RULES.parameters, key))


def test_a_planted_script_is_refused_with_the_legal_home_and_the_move(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path)
    write(repo, "scripts/new_tool.py", "a = 1\n")
    git(repo, "add", "-A")
    found = [i for i in issues(repo) if i.code == "noncanonical-file"]
    assert [i.file_path.as_posix() for i in found] == ["scripts/new_tool.py"]
    _assert_names_home_and_move(found[0].message)


def test_a_planted_shell_script_is_refused_with_the_legal_home_and_the_move(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path)
    write(repo, "scripts/new_tool.sh", "#!/bin/sh\ntrue\n")
    git(repo, "add", "-A")
    found = [i for i in issues(repo) if i.code == "noncanonical-file"]
    assert [i.file_path.as_posix() for i in found] == ["scripts/new_tool.sh"]
    _assert_names_home_and_move(found[0].message)


def test_a_planted_node_directory_is_refused_with_the_legal_home_and_the_move(
    tmp_path: Path,
) -> None:
    git(tmp_path, "init", "-q", "-b", "dev")
    write(tmp_path, "pyproject.toml", '[project]\nname = "other_repo"\n')
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "initial")
    _plant(tmp_path, "src/pkg/nodes/node_fresh", "name: fresh\n")
    git(tmp_path, "add", "-A")
    findings = NodeHomeRule(RULES).check(_request(tmp_path)).findings
    assert [f.code for f in findings] == ["node-outside-market"]
    _assert_names_home_and_move(findings[0].message)
