# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Characterization tests for node_source_file_gather_effect (OMN-14656).

These tests encode the expected behavior of the archived
``DirectoryTraverser.find_files`` / ``_find_files_with_config``
(``omnibase_archived/src/omnibase/utils/directory_traverser.py:129-387``) as
golden expected values, since ``omnibase_archived`` is not an installed
dependency of ``omnibase_core`` (and should not become one — it is a
demoted legacy package outside the compat -> core -> spi -> infra layering).
Each case below traces back to a specific oracle code path cited in its
docstring/comment.

Covers:
- Basic recursive gather with content-inline output
- FLAT / SHALLOW / RECURSIVE traversal-mode eligibility scoping
- .onexignore-sourced ignore patterns (walking to the .git boundary)
- Caller-supplied exclude_patterns
- Default ignore directories (.venv, venv, ...) pruned unconditionally
- source_only pruning of env/.env (OMN-9537 extension)
- Schema-file exclusion (directory name and filename pattern)
- max_file_size skip
- Non-existent / non-directory root returns an empty result
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums.enum_ignore_pattern_source import EnumTraversalMode
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)

pytestmark = pytest.mark.unit


def _skip_reasons(output) -> dict[str, str]:
    return {Path(s.path).name: s.reason for s in output.skipped}


def _file_names(output) -> set[str]:
    return {Path(f.path).name for f in output.files}


# =============================================================================
# Basic recursive gather
# =============================================================================


def test_recursive_gather_returns_content_inline(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("y = 2\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(root=str(tmp_path), include_patterns=["**/*.py"])
    )

    assert _file_names(output) == {"a.py", "b.py"}
    by_name = {Path(f.path).name: f for f in output.files}
    assert by_name["a.py"].source == "x = 1\n"
    assert by_name["a.py"].size_bytes == len("x = 1\n")
    assert output.root == str(tmp_path)
    assert output.skipped == []


def test_non_matching_extension_is_not_gathered(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "readme.md").write_text("# hi\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(root=str(tmp_path), include_patterns=["**/*.py"])
    )

    assert _file_names(output) == {"a.py"}


# =============================================================================
# Traversal mode eligibility (directory_traverser.py:320-330)
# =============================================================================


def test_flat_mode_glob_is_single_level_so_subdir_files_are_never_seen(
    tmp_path: Path,
) -> None:
    """FLAT mode's glob itself is non-recursive (oracle: ``recursive = mode in
    [RECURSIVE, SHALLOW]``, directory_traverser.py:213-216) — a ``**/``-form
    pattern is stripped down to a single-level pattern
    (directory_traverser.py:272-273), so ``sub/b.py`` is never even a glob
    candidate. It therefore does not appear in ``skipped`` either."""
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("y = 2\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(
            root=str(tmp_path),
            include_patterns=["**/*.py"],
            traversal_mode=EnumTraversalMode.FLAT,
        )
    )

    assert _file_names(output) == {"a.py"}
    assert output.skipped == []


def test_flat_mode_explicit_subdir_pattern_is_skipped_with_reason(
    tmp_path: Path,
) -> None:
    """An explicit (non-``**/``-prefixed) subdirectory-spanning pattern still
    reaches the glob in FLAT mode, so the per-file eligibility filter's
    "not in directory (FLAT mode)" skip reason (directory_traverser.py:320-324)
    is reachable."""
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("y = 2\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(
            root=str(tmp_path),
            include_patterns=["sub/*.py"],
            traversal_mode=EnumTraversalMode.FLAT,
        )
    )

    assert output.files == []
    assert _skip_reasons(output)["b.py"] == "not in directory (FLAT mode)"


def test_shallow_mode_includes_root_and_immediate_subdir_only(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("y = 2\n")
    (tmp_path / "sub" / "sub2").mkdir()
    (tmp_path / "sub" / "sub2" / "c.py").write_text("z = 3\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(
            root=str(tmp_path),
            include_patterns=["**/*.py"],
            traversal_mode=EnumTraversalMode.SHALLOW,
        )
    )

    assert _file_names(output) == {"a.py", "b.py"}
    assert (
        _skip_reasons(output)["c.py"] == "not in immediate subdirectory (SHALLOW mode)"
    )


def test_recursive_mode_includes_all_depths(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "sub2").mkdir()
    (tmp_path / "sub" / "sub2" / "c.py").write_text("z = 3\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(
            root=str(tmp_path),
            include_patterns=["**/*.py"],
            traversal_mode=EnumTraversalMode.RECURSIVE,
        )
    )

    assert _file_names(output) == {"c.py"}


# =============================================================================
# Ignore patterns
# =============================================================================


def test_onexignore_directory_pattern_is_pruned(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()  # repo-root boundary for load_ignore_patterns
    (tmp_path / ".onexignore").write_text("all:\n  patterns:\n    - ignored_dir/\n")
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "ignored_dir").mkdir()
    (tmp_path / "ignored_dir" / "b.py").write_text("y = 2\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(
            root=str(tmp_path), include_patterns=["**/*.py"], ignore_file=str(tmp_path)
        )
    )

    assert _file_names(output) == {"a.py"}
    assert _skip_reasons(output)["b.py"] == "ignored by pattern"


def test_onexignore_stamper_patterns_are_also_applied(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".onexignore").write_text(
        "stamper:\n  patterns:\n    - '*_generated.py'\n"
    )
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b_generated.py").write_text("y = 2\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(
            root=str(tmp_path), include_patterns=["**/*.py"], ignore_file=str(tmp_path)
        )
    )

    assert _file_names(output) == {"a.py"}
    assert _skip_reasons(output)["b_generated.py"] == "ignored by pattern"


def test_onexignore_unknown_top_level_sections_do_not_break_parsing(
    tmp_path: Path,
) -> None:
    """Real ``.onexignore`` files carry many check-specific sections beyond
    ``all``/``stamper`` (e.g. ``check-direct-tool-imports`` in
    ``omnibase_archived/.onexignore``). The canonical
    ``omnibase_core.models.core.model_onex_ignore.ModelOnexIgnore`` parse
    path (OMN-14656 remediation, replacing raw ``yaml.safe_load``) only
    declares ``stamper``/``validator``/``tree``/``all`` fields, so unknown
    top-level keys are dropped rather than raising, and ``all``/``stamper``
    patterns are still applied."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".onexignore").write_text(
        "check-direct-tool-imports:\n"
        "  patterns:\n"
        "    - some/unrelated/path.py\n"
        "all:\n"
        "  patterns:\n"
        "    - ignored_dir/\n"
    )
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "ignored_dir").mkdir()
    (tmp_path / "ignored_dir" / "b.py").write_text("y = 2\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(
            root=str(tmp_path), include_patterns=["**/*.py"], ignore_file=str(tmp_path)
        )
    )

    assert _file_names(output) == {"a.py"}
    assert _skip_reasons(output)["b.py"] == "ignored by pattern"


def test_onexignore_malformed_yaml_contributes_no_patterns(tmp_path: Path) -> None:
    """Unparseable/structurally-invalid ``.onexignore`` degrades to zero
    patterns (fallback-ok) rather than raising out of the EFFECT handler."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".onexignore").write_text("not: [valid, - yaml: broken\n")
    (tmp_path / "a.py").write_text("x = 1\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(
            root=str(tmp_path), include_patterns=["**/*.py"], ignore_file=str(tmp_path)
        )
    )

    assert _file_names(output) == {"a.py"}
    assert output.skipped == []


def test_exclude_patterns_are_applied(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b_skip.py").write_text("y = 2\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(
            root=str(tmp_path),
            include_patterns=["**/*.py"],
            exclude_patterns=["*_skip.py"],
        )
    )

    assert _file_names(output) == {"a.py"}
    assert _skip_reasons(output)["b_skip.py"] == "ignored by pattern"


def test_default_ignore_dirs_pruned_unconditionally(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "site.py").write_text("y = 2\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(root=str(tmp_path), include_patterns=["**/*.py"])
    )

    assert _file_names(output) == {"a.py"}
    assert _skip_reasons(output)["site.py"] == "ignored by pattern"


def test_source_only_prunes_env_directory(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "env").mkdir()
    (tmp_path / "env" / "site.py").write_text("y = 2\n")

    handler = NodeSourceFileGatherEffect()

    without_source_only = handler.handle(
        ModelSourceFileGatherInput(
            root=str(tmp_path), include_patterns=["**/*.py"], source_only=False
        )
    )
    assert _file_names(without_source_only) == {"a.py", "site.py"}

    with_source_only = handler.handle(
        ModelSourceFileGatherInput(
            root=str(tmp_path), include_patterns=["**/*.py"], source_only=True
        )
    )
    assert _file_names(with_source_only) == {"a.py"}
    assert _skip_reasons(with_source_only)["site.py"] == "ignored by pattern"


# =============================================================================
# Schema exclusion (directory_traverser.py:38-77)
# =============================================================================


def test_schema_directory_is_excluded(tmp_path: Path) -> None:
    (tmp_path / "schemas").mkdir()
    (tmp_path / "schemas" / "foo.yaml").write_text("a: 1\n")
    (tmp_path / "bar.yaml").write_text("b: 2\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(root=str(tmp_path), include_patterns=["**/*.yaml"])
    )

    assert _file_names(output) == {"bar.yaml"}
    assert _skip_reasons(output)["foo.yaml"] == "schema file"


def test_schema_filename_pattern_is_excluded(tmp_path: Path) -> None:
    (tmp_path / "onex_node.yaml").write_text("a: 1\n")
    (tmp_path / "bar.yaml").write_text("b: 2\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(root=str(tmp_path), include_patterns=["**/*.yaml"])
    )

    assert _file_names(output) == {"bar.yaml"}
    assert _skip_reasons(output)["onex_node.yaml"] == "schema file"


# =============================================================================
# max_file_size
# =============================================================================


def test_files_exceeding_max_file_size_are_skipped(tmp_path: Path) -> None:
    (tmp_path / "small.py").write_text("x = 1\n")
    (tmp_path / "big.py").write_text("y" * 100)

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(
            root=str(tmp_path), include_patterns=["**/*.py"], max_file_size=10
        )
    )

    assert _file_names(output) == {"small.py"}
    assert _skip_reasons(output)["big.py"] == "exceeds max file size"


# =============================================================================
# Root existence (directory_traverser.py:208-209)
# =============================================================================


def test_nonexistent_root_returns_empty_result(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(root=str(missing), include_patterns=["**/*.py"])
    )

    assert output.files == []
    assert output.skipped == []
    assert output.root == str(missing)


def test_root_that_is_a_file_returns_empty_result(tmp_path: Path) -> None:
    not_a_dir = tmp_path / "file.txt"
    not_a_dir.write_text("hello\n")

    handler = NodeSourceFileGatherEffect()
    output = handler.handle(
        ModelSourceFileGatherInput(root=str(not_a_dir), include_patterns=["**/*.py"])
    )

    assert output.files == []
    assert output.skipped == []


# =============================================================================
# NOTE: an fnmatch-based fallback matcher (exercised when pathspec is
# unavailable, directory_traverser.py:556-668) previously lived here as a
# monkeypatch-forced test. It was removed under OMN-14656 remediation:
# pathspec is now a hard runtime dependency of omnibase_core (no
# optional-import fallback — see handler.py._should_ignore), so there is no
# fallback branch left to exercise. Directory-pattern and glob-pattern
# ignore-matching via pathspec are already covered by
# test_onexignore_directory_pattern_is_pruned,
# test_exclude_patterns_are_applied, and
# test_default_ignore_dirs_pruned_unconditionally above.
# =============================================================================
