# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression tests for the executable string-version pre-commit hook."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPOSITORY_ROOT = Path(__file__).parents[2]
_HOOK = _REPOSITORY_ROOT / "scripts" / "validation" / "validate-string-versions.py"
_REGISTRY = (
    _REPOSITORY_ROOT
    / "src"
    / "omnibase_core"
    / "contracts"
    / "antipattern_registry.yaml"
)


def _run_hook(*paths: Path) -> subprocess.CompletedProcess[str]:
    """Run the executable hook exactly against the supplied files."""
    return subprocess.run(
        [sys.executable, str(_HOOK), *(str(path) for path in paths)],
        cwd=_REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_allows_string_version_only_for_validated_canonical_registry() -> None:
    """The registry's model-owned version remains a string by contract."""
    completed = _run_hook(_REGISTRY)

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_rejects_same_registry_schema_at_noncanonical_path(tmp_path: Path) -> None:
    """A matching document elsewhere cannot bypass the version policy."""
    copy = tmp_path / "antipattern_registry.yaml"
    copy.write_text(_REGISTRY.read_text(encoding="utf-8"), encoding="utf-8")

    completed = _run_hook(copy)

    assert completed.returncode == 1
    assert "Field 'version' uses string version '1.0.0'" in completed.stdout


def test_allows_ruff_formatted_field_rationale(tmp_path: Path) -> None:
    """A rationale on the immediate ``Field`` continuation is intentional."""
    source = tmp_path / "model.py"
    source.write_text(
        """
class ModelExample:
    served_model_id: str = (
        Field(  # string-id-ok: external provider identity, not a UUID
            description="External provider identifier"
        )
    )
""",
        encoding="utf-8",
    )

    completed = _run_hook(source)

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_rejects_marker_after_field_continuation(tmp_path: Path) -> None:
    """Only the formatter-produced Field-line marker can exempt a field."""
    source = tmp_path / "model.py"
    source.write_text(
        """
class ModelExample:
    served_model_id: str = (
        Field(description="External provider identifier")
    )  # string-id-ok: this trailing marker is not the field declaration
""",
        encoding="utf-8",
    )

    completed = _run_hook(source)

    assert completed.returncode == 1
    assert "Field 'served_model_id'" in completed.stdout


@pytest.mark.parametrize(
    "field_body",
    [
        """
        helper(  # string-id-ok: arbitrary call is not the Field continuation
            description="External provider identifier"
        )
""",
        """
        Field(
            description="External provider identifier"
        )
        # string-id-ok: a later line cannot exempt the field
""",
        """
        Field(description="# string-id-ok: string data is not a comment")
""",
        """
        Field(  # not-string-id-ok: only the exact marker is accepted
            description="External provider identifier"
        )
""",
    ],
)
def test_rejects_nonadjacent_or_noncomment_field_markers(
    tmp_path: Path, field_body: str
) -> None:
    """Only an adjacent, exact comment marker may exempt a Pydantic field."""
    source = tmp_path / "model.py"
    source.write_text(
        f"""
class ModelExample:
    served_model_id: str = (
{field_body}    )
""",
        encoding="utf-8",
    )

    completed = _run_hook(source)

    assert completed.returncode == 1
    assert "Field 'served_model_id'" in completed.stdout
