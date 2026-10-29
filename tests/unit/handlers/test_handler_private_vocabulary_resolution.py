# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The composition root for private-vocabulary resolution (OMN-21494).

The only file reads are the source-file gather effect node's, which the root
resolves from the container beside the contract-injected pure handler.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_private_vocabulary_resolution import (
    build_container,
    read_file_fact,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler_private_vocabulary import (
    HandlerPrivateVocabulary,
)
from omnibase_core.validators.handler_di_gate import validate_paths

pytestmark = pytest.mark.unit

_SRC = Path(__file__).resolve().parents[3] / "src" / "omnibase_core"

_HYGIENE_ENV = "OMNI_HYGIENE_VOCAB_PATH"
_ROOT_ENV = "ONEX_WORKSPACE_CONFIG_ROOT"


def test_the_effect_reports_a_file_and_its_text(tmp_path: Path) -> None:
    target = tmp_path / "v.yaml"
    target.write_text("schema_version: 1\n", encoding="utf-8")
    fact = read_file_fact(NodeSourceFileGatherEffect(), target)
    assert (fact.path, fact.is_file, fact.text, fact.error) == (
        target,
        True,
        "schema_version: 1\n",
        None,
    )


def test_a_missing_path_is_not_a_file_and_not_an_error(tmp_path: Path) -> None:
    fact = read_file_fact(NodeSourceFileGatherEffect(), tmp_path / "absent.yaml")
    assert (fact.is_file, fact.text, fact.error) == (False, None, None)


def test_a_directory_is_not_a_file_and_not_an_error(tmp_path: Path) -> None:
    fact = read_file_fact(NodeSourceFileGatherEffect(), tmp_path)
    assert (fact.is_file, fact.text, fact.error) == (False, None, None)


def test_undecodable_text_is_one_error_line(tmp_path: Path) -> None:
    target = tmp_path / "bad.yaml"
    target.write_bytes(b"\xff\xfe\x00bad")
    fact = read_file_fact(NodeSourceFileGatherEffect(), target)
    assert fact.is_file is False
    assert fact.text is None
    assert fact.error is not None
    assert str(target) in fact.error
    assert "\n" not in fact.error


def test_a_file_is_read_whatever_its_name_or_directory(tmp_path: Path) -> None:
    target = tmp_path / ".github" / "vocab.txt"
    target.parent.mkdir()
    target.write_text("x: 1\n", encoding="utf-8")
    assert read_file_fact(NodeSourceFileGatherEffect(), target).text == "x: 1\n"


def test_the_container_holds_the_gather_effect_and_the_contract_injected_handler() -> (
    None
):
    container = build_container()
    assert isinstance(
        container.get_service(NodeSourceFileGatherEffect), NodeSourceFileGatherEffect
    )
    handler = container.get_service(HandlerPrivateVocabulary)
    assert {_HYGIENE_ENV, _ROOT_ENV} <= handler.declared_environment_keys()


def test_an_invalid_contract_is_one_refusal_line(tmp_path: Path) -> None:
    broken = tmp_path / "contract.yaml"
    broken.write_text("schema_version: [\n", encoding="utf-8")
    with pytest.raises(ModelOnexError) as caught:
        build_container(broken)
    assert "\n" not in caught.value.message


def test_a_missing_contract_is_one_refusal_line(tmp_path: Path) -> None:
    with pytest.raises(ModelOnexError) as caught:
        build_container(tmp_path / "absent.yaml")
    assert "\n" not in caught.value.message


def test_the_handler_di_gate_reports_nothing_on_the_handler_and_its_root() -> None:
    changed = [
        _SRC
        / "nodes"
        / "node_source_file_gather_effect"
        / "handler_private_vocabulary.py",
        _SRC / "handlers" / "handler_private_vocabulary_resolution.py",
    ]
    assert validate_paths(changed) == []


def test_the_handler_di_gate_flags_a_handler_that_defaults_its_contract(
    tmp_path: Path,
) -> None:
    planted = tmp_path / "handlers" / "handler_planted.py"
    planted.parent.mkdir()
    planted.write_text(
        "class HandlerPlanted:\n"
        "    def __init__(self, contract=None):\n"
        "        self._contract = contract\n",
        encoding="utf-8",
    )
    assert len(validate_paths([planted])) == 1


def test_no_source_builds_the_handler_at_a_call_site_or_defaults_a_contract() -> None:
    for path in _SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "HandlerPrivateVocabulary()" not in text, path
    handler_text = (
        _SRC
        / "nodes"
        / "node_source_file_gather_effect"
        / "handler_private_vocabulary.py"
    ).read_text(encoding="utf-8")
    assert "contract=None" not in handler_text
