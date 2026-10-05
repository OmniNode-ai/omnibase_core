# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Synthetic repository corpus and sibling-oracle evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.test_root_collection_check.model_test_root_collection_check_input import (
    ModelTestRootCollectionCheckInput,
)
from omnibase_core.nodes.node_test_root_collection_check_compute.matcher_test_root_collection import (
    selector_from_source,
)

pytestmark = pytest.mark.unit
REPO_ROOT = Path(__file__).resolve().parents[4]
CORPUS_ROOT = REPO_ROOT / "tests/fixtures/validator_parity/test_root_collection"
CORPUS = json.loads((CORPUS_ROOT / "corpus.json").read_text())
GOLDEN = json.loads((CORPUS_ROOT / "golden.json").read_text())
CASES = {case["name"]: case for case in CORPUS["cases"]}


def materialize_parity_case(root: Path, name: str) -> None:
    case = CASES[name]
    for directory in case["directories"]:
        (root / directory).mkdir(parents=True, exist_ok=True)
    for relative, source in case["files"].items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    for relative, encoded in case.get("binary_files", {}).items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bytes.fromhex(encoded))


def parity_request(root: Path, name: str) -> ModelTestRootCollectionCheckInput:
    case = CASES[name]
    directories = set(case["directories"])
    for relative in case["files"]:
        directories.update(str(parent) for parent in Path(relative).parents)
    selector_source = case["files"].get("scripts/ci/detect_test_paths.py")
    return ModelTestRootCollectionCheckInput(
        files=[
            ModelSourceFile(path=path, source=source)
            for path, source in case["files"].items()
        ],
        directories=tuple(sorted(directories)),
        test_files=tuple(
            path for path in case["files"] if Path(path).match("test_*.py")
        ),
        standalone_pyprojects=tuple(
            path
            for path in set(case["files"]) | set(case.get("binary_files", {}))
            if path.endswith("/pyproject.toml")
        ),
        selector=selector_from_source(selector_source, str(root.resolve())),
        root_label=str(root.resolve()),
    )


def normalize_parity_message(message: str, root: Path) -> str:
    return message.replace(str(root.resolve()), "<root>").replace(str(root), "<root>")
