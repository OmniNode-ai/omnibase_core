# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from pathlib import Path

import pytest

from omnibase_core.enums.enum_file_zone import EnumFileZone
from omnibase_core.validation.zone_classifier import classify_path

pytestmark = pytest.mark.unit


def test_classify_production() -> None:
    assert classify_path(Path("src/omnibase_core/foo.py")) == EnumFileZone.PRODUCTION


def test_classify_test() -> None:
    assert classify_path(Path("tests/test_foo.py")) == EnumFileZone.TEST


def test_classify_config_yaml_outside_src() -> None:
    assert classify_path(Path("pyproject.toml")) == EnumFileZone.CONFIG


def test_classify_yaml_inside_src_is_production() -> None:
    # config files inside src/ are part of the package, not free config
    assert (
        classify_path(Path("src/omnibase_core/contracts/foo.yaml"))
        == EnumFileZone.PRODUCTION
    )


def test_classify_generated_wins_over_production() -> None:
    # priority: generated > production > test > config > docs > build
    assert (
        classify_path(Path("src/__pycache__/foo.cpython-312.pyc"))
        == EnumFileZone.GENERATED
    )


def test_classify_docs() -> None:
    assert classify_path(Path("docs/architecture.md")) == EnumFileZone.DOCS


def test_classify_contracts_yaml_is_docs() -> None:
    # Top-level contracts/ holds OCC ticket contracts — declarative evidence,
    # no runtime impact, must skip the heavy matrix.
    assert classify_path(Path("contracts/OMN-10411.yaml")) == EnumFileZone.DOCS


def test_classify_dod_receipts_yaml_is_docs() -> None:
    assert (
        classify_path(Path("drift/dod_receipts/OMN-10411/dod-001/command.yaml"))
        == EnumFileZone.DOCS
    )


def test_classify_allowlists_yaml_is_docs() -> None:
    assert classify_path(Path("allowlists/skip_tokens.yaml")) == EnumFileZone.DOCS


def test_classify_evidence_yaml_is_docs() -> None:
    # Legacy .evidence/ tree
    assert classify_path(Path(".evidence/OMN-9999/proof.yaml")) == EnumFileZone.DOCS


def test_src_contracts_yaml_stays_production() -> None:
    # Crucially: a contracts/ directory inside src/ is package code, not
    # declarative evidence — production gate must still apply.
    assert (
        classify_path(Path("src/omnibase_core/nodes/foo/contracts/contract.yaml"))
        == EnumFileZone.PRODUCTION
    )


def test_root_contract_yaml_stays_production_via_src() -> None:
    # node-local contract.yaml under src/ — runtime behavior, full matrix.
    assert (
        classify_path(Path("src/omnimarket/nodes/node_foo/contract.yaml"))
        == EnumFileZone.PRODUCTION
    )


def test_pyproject_toml_stays_config() -> None:
    # Sanity: build/runtime config at repo root is still CONFIG, not DOCS.
    assert classify_path(Path("pyproject.toml")) == EnumFileZone.CONFIG


def test_metadata_yaml_stays_config() -> None:
    assert classify_path(Path("metadata.yaml")) == EnumFileZone.CONFIG


def test_workflow_yaml_stays_config() -> None:
    # CI workflows are not declarative evidence — they affect every run.
    assert classify_path(Path(".github/workflows/ci.yml")) == EnumFileZone.CONFIG


def test_classify_build() -> None:
    assert classify_path(Path("scripts/deploy.sh")) == EnumFileZone.BUILD


def test_existing_contracts_file_classifies_as_docs(tmp_path: Path) -> None:
    # Regression for CodeRabbit finding on PR #1023: when the changed file
    # actually exists on disk, classify_path() previously resolved it to an
    # absolute path (e.g. /tmp/.../contracts/X.yaml) and the bare
    # `s.startswith("contracts/")` check missed it, dropping the file into
    # CONFIG and defeating the docs-only short-circuit in CI.
    target = tmp_path / "contracts" / "OMN-1234.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("---\n")
    assert classify_path(target) == EnumFileZone.DOCS


def test_existing_dod_receipts_file_classifies_as_docs(tmp_path: Path) -> None:
    target = (
        tmp_path / "drift" / "dod_receipts" / "OMN-1234" / "dod-001" / "command.yaml"
    )
    target.parent.mkdir(parents=True)
    target.write_text("status: PASS\n")
    assert classify_path(target) == EnumFileZone.DOCS


def test_symlink_resolved_before_classification(tmp_path: Path) -> None:
    target = tmp_path / "src" / "real.py"
    target.parent.mkdir(parents=True)
    target.write_text("")
    link = tmp_path / "link.py"
    link.symlink_to(target)
    assert classify_path(link) == EnumFileZone.PRODUCTION
