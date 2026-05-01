# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pathlib import Path

import pytest

from omnibase_core.validation.completion_verify import resolve_file_targets


def test_extracts_quoted_paths():
    out = resolve_file_targets(
        'Touch "src/foo.py" and `tests/bar.py`', project_root=Path()
    )
    paths = {p.name for p in out}
    assert paths == {"foo.py", "bar.py"}


def test_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="escapes"):
        resolve_file_targets('Touch "../../etc/passwd"', project_root=tmp_path)


def test_uses_files_touched_field():
    out = resolve_file_targets("done", project_root=Path(), files_touched=["src/x.py"])
    assert out == [Path("src/x.py").resolve()]


def test_deduplicates_paths():
    out = resolve_file_targets(
        'Touch "src/foo.py" and "src/foo.py"', project_root=Path()
    )
    names = [p.name for p in out]
    assert names.count("foo.py") == 1


def test_no_paths_returns_empty():
    out = resolve_file_targets("nothing here", project_root=Path())
    assert out == []


def test_files_touched_combined_with_text(tmp_path):
    out = resolve_file_targets(
        'Touch "src/other.py"', project_root=tmp_path, files_touched=["src/real.py"]
    )
    names = {p.name for p in out}
    assert "real.py" in names
    assert "other.py" in names
