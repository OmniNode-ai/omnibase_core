# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The no_io_outside_effects replay adapter reaches its checker for a module no node contract sits above.

The adapter used to return before calling the checker when it found no node contract, so an
assertion about such a module (F28-1) could not be met however strong the checker was. The
checker judges that module itself; the adapter hands it over.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.andon_replay import driver
from tests.fixtures.andon_replay.adapters import (
    adapter_no_io_outside_effects as adapter,
)

pytestmark = pytest.mark.unit

_VALIDATOR_ID = "no_io_outside_effects"
_RULE_ID = "file_read"
_MODULE = "handlers/handler_x.py"
_VIOLATION = '''"""Planted: a handler that no node contract sits above reads a file."""

from pathlib import Path


class HandlerX:
    def handle(self, request: Path) -> str:
        return request.read_text(encoding="utf-8")
'''
_CLEAN = '''"""Clean: a handler that no node contract sits above takes the text in its request."""


class HandlerX:
    def handle(self, request: str) -> str:
        return request.strip()
'''


def _replay(tmp_path: Path, body: str) -> list[str]:
    corpus = driver.load_corpus(driver.DEFAULT_CORPUS_PATH)
    contract = driver.load_contracts(corpus, driver.repo_root(corpus))[_VALIDATOR_ID]
    (tmp_path / _MODULE).parent.mkdir(parents=True)
    (tmp_path / _MODULE).write_text(body, encoding="utf-8")
    run = driver.ReplayRun(
        validator_id=_VALIDATOR_ID,
        contract=contract,
        source=driver.directory_source(tmp_path, _MODULE),
        rule_id=_RULE_ID,
    )
    return [i.code for i in adapter.replay(run) if i.code]


def test_a_module_with_no_node_contract_reaches_the_checker(tmp_path: Path) -> None:
    assert _replay(tmp_path, _VIOLATION) == [_RULE_ID]


def test_a_clean_module_with_no_node_contract_reports_nothing(tmp_path: Path) -> None:
    assert _replay(tmp_path, _CLEAN) == []
