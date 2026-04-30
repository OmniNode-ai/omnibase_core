# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_completion_verify_result import (
    ModelCompletionVerifyResult,
)
from omnibase_core.validation.completion_verify import verify


def test_verify_finds_identifier(tmp_path: Path) -> None:
    f = tmp_path / "src" / "x.py"
    f.parent.mkdir(parents=True)
    f.write_text("def fooBar(): ...")
    result = verify(
        task_id="OMN-1",
        description="Implement `fooBar`",
        files_touched=["src/x.py"],
        project_root=tmp_path,
    )
    assert isinstance(result, ModelCompletionVerifyResult)
    assert result.found == {"fooBar": str(f.resolve())}
    assert result.missing == []
    assert not result.skipped


def test_verify_missing(tmp_path: Path) -> None:
    f = tmp_path / "src" / "x.py"
    f.parent.mkdir(parents=True)
    f.write_text("# nothing here")
    result = verify(
        task_id="OMN-1",
        description="Implement `fooBar`",
        files_touched=["src/x.py"],
        project_root=tmp_path,
    )
    assert "fooBar" in result.missing


def test_verify_skips_when_no_files(tmp_path: Path) -> None:
    result = verify(
        task_id="OMN-RESEARCH",
        description="Investigate Kafka topic naming",
        files_touched=None,
        project_root=tmp_path,
    )
    assert result.skipped
    assert result.skipped_reason is not None


def test_verify_multiple_identifiers_across_files(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir(parents=True)
    (src / "a.py").write_text("class ModelFoo: ...")
    (src / "b.py").write_text("def validateToken(): ...")
    result = verify(
        task_id="OMN-2",
        description="Add `ModelFoo` and `validateToken`",
        files_touched=["src/a.py", "src/b.py"],
        project_root=tmp_path,
    )
    assert "ModelFoo" in result.found
    assert "validateToken" in result.found
    assert result.missing == []


def test_verify_skips_when_empty_files_touched(tmp_path: Path) -> None:
    result = verify(
        task_id="OMN-3",
        description="Research something",
        files_touched=[],
        project_root=tmp_path,
    )
    assert result.skipped
    assert result.skipped_reason is not None


@pytest.mark.unit
def test_verify_returns_frozen_result(tmp_path: Path) -> None:
    f = tmp_path / "src" / "x.py"
    f.parent.mkdir(parents=True)
    f.write_text("def fooBar(): ...")
    result = verify(
        task_id="OMN-1",
        description="Implement `fooBar`",
        files_touched=["src/x.py"],
        project_root=tmp_path,
    )
    with pytest.raises(Exception):
        result.task_id = "CHANGED"  # type: ignore[misc]
