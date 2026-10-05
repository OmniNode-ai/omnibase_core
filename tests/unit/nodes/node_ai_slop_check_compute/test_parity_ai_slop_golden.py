# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Permanent parity against core script-generated fixture goldens."""

import json
from pathlib import Path

import pytest

from .parity_helpers import (
    CORPUS,
    FIXTURES,
    GOLDEN,
    ROOT,
    handler_parity,
    normalized_parity,
    rows_parity,
    runtime_parity,
    tree_paths_parity,
)

pytestmark = pytest.mark.unit
CONFIG_CORPUS: dict[str, str] = json.loads(
    (FIXTURES / "config_corpus.json").read_text()
)
CONFIG_GOLDEN = json.loads((FIXTURES / "config_golden.json").read_text())


@pytest.mark.parametrize("name", sorted(CORPUS))
@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("report", [False, True])
def test_parity_ai_slop_golden(
    name: str, strict: bool, report: bool, tmp_path: Path
) -> None:
    path = tmp_path / name
    path.write_text(CORPUS[name])
    expected = GOLDEN[name][f"{int(strict)}:{int(report)}"]
    code, result = runtime_parity([path], strict, report, tmp_path / "result.json")
    assert code == expected["exit_code"]
    for actual in (
        rows_parity(result),
        rows_parity(handler_parity([path], strict, report)),
    ):
        for row in actual:
            row["filename"] = name
        assert normalized_parity(actual) == normalized_parity(expected["findings"])


@pytest.mark.parametrize("strict", [False, True])
def test_parity_ai_slop_source_tree_golden(strict: bool, tmp_path: Path) -> None:
    assert len(tree_paths_parity()) > 0
    expected = json.loads((FIXTURES / "tree_golden.json").read_text())[str(int(strict))]
    code, result = runtime_parity(
        [], strict, False, tmp_path / "result.json", ["--root", str(ROOT / "src")]
    )
    rows = rows_parity(result)
    for row in rows:
        row["filename"] = str(Path(str(row["filename"])).relative_to(ROOT))
    assert code == expected["exit_code"]
    assert normalized_parity(rows) == normalized_parity(expected["findings"])


def test_parity_ai_slop_ci_tree_golden(tmp_path: Path) -> None:
    paths = [ROOT / p for p in json.loads((FIXTURES / "ci_scope.json").read_text())]
    expected = json.loads((FIXTURES / "ci_golden.json").read_text())
    assert len(paths) == expected["files_scanned"] > 0
    code, result = runtime_parity(paths, True, False, tmp_path / "report.json")
    rows = rows_parity(result)
    for row in rows:
        row["filename"] = str(Path(str(row["filename"])).relative_to(ROOT))
    assert code == expected["exit_code"]
    assert normalized_parity(rows) == normalized_parity(expected["findings"])


@pytest.mark.parametrize("name", sorted(CONFIG_CORPUS))
@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("report", [False, True])
def test_parity_ai_slop_config_golden(
    name: str, strict: bool, report: bool, tmp_path: Path
) -> None:
    config = tmp_path / ".onex"
    config.mkdir()
    (config / "aislop-rules.yaml").write_text(CONFIG_CORPUS[name])
    source = tmp_path / "source.py"
    source.write_text('"""Great! Welcome.\n:param x: input\nflagme\n"""\n# flagme\n')
    expected = CONFIG_GOLDEN[name][f"{int(strict)}:{int(report)}"]
    code, result = runtime_parity(
        [source], strict, report, tmp_path / "result.json", ["--config", str(tmp_path)]
    )
    assert code == expected["exit_code"]
    for rows in (
        rows_parity(result),
        rows_parity(handler_parity([source], strict, report, tmp_path)),
    ):
        for row in rows:
            row["filename"] = source.name
        assert normalized_parity(rows) == normalized_parity(expected["findings"])
