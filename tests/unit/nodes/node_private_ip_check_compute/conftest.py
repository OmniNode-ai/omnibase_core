# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Materialize the escaped acceptance corpus without source suppressions."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def parity_corpus(tmp_path: Path) -> Path:
    fixture = (
        Path(__file__).resolve().parents[3]
        / "fixtures/validator_parity/private_ip/corpus.json"
    )
    corpus: dict[str, str] = json.loads(fixture.read_text())
    root = tmp_path / "corpus"
    for name, source in corpus.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return root
