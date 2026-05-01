# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from pathlib import Path

from omnibase_core.enums.enum_file_zone import EnumFileZone
from omnibase_core.validation.zone_classifier import classify_path


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


def test_classify_build() -> None:
    assert classify_path(Path("scripts/deploy.sh")) == EnumFileZone.BUILD


def test_symlink_resolved_before_classification(tmp_path: Path) -> None:
    target = tmp_path / "src" / "real.py"
    target.parent.mkdir(parents=True)
    target.write_text("")
    link = tmp_path / "link.py"
    link.symlink_to(target)
    assert classify_path(link) == EnumFileZone.PRODUCTION
