# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the hook-writes rule (OMN-21433, plan task T2.6).

A pre-commit hook must check, never rewrite: a hook whose entry (or a known
rewriting hook id from a remote repository) changes files is a FAIL. The signals
are the overlay's rule values; these tests load the repository's own overlay so
the values that gate the repository are the values under test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_hook_writes import HandlerHookWrites
from omnibase_core.models.hook_writes import (
    ModelHookWritesCheckInput,
    ModelHookWritesOverlay,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONFIG = ".pre-commit-config.yaml"
_EXPORTED = ".pre-commit-hooks.yaml"


@pytest.fixture(scope="module")
def overlay() -> ModelHookWritesOverlay:
    return load_and_validate_yaml_model(
        _ROOT / ".hook-writes-overlay.yaml", ModelHookWritesOverlay
    )


def _local(*hooks: str) -> str:
    return "repos:\n  - repo: local\n    hooks:\n" + "".join(hooks)


def _hook(hook_id: str, entry: str, extra: str = "") -> str:
    return (
        f"      - id: {hook_id}\n"
        f"        name: {hook_id}\n"
        f"        entry: {json.dumps(entry)}\n"
        "        language: system\n" + extra
    )


def _run(
    overlay: ModelHookWritesOverlay, source: str, path: str = _CONFIG
) -> ModelValidationReport:
    return HandlerHookWrites().handle(
        ModelHookWritesCheckInput(
            overlay=overlay, files=(ModelSourceFile(path=path, source=source),)
        )
    )


def _fails(report: ModelValidationReport) -> list[str]:
    return [f.message for f in report.findings if f.severity == "FAIL"]


class TestWritingEntries:
    @pytest.mark.parametrize(
        "entry",
        [
            "uv run ruff format --force-exclude",
            "uv run ruff check --force-exclude --fix --exit-non-zero-on-fix",
            "perl -i -ne 'print unless /x/'",
            "sed -i 's/a/b/' file.txt",
            'bash -c "rm -rf tmp/* 2>/dev/null || true"',
            "git add -A",
            "prettier --write",
        ],
    )
    def test_writing_entry_fails(
        self, overlay: ModelHookWritesOverlay, entry: str
    ) -> None:
        report = _run(overlay, _local(_hook("some-hook", entry)))
        assert report.overall_status == "FAIL"
        assert len(_fails(report)) == 1
        assert "some-hook" in _fails(report)[0]

    @pytest.mark.parametrize(
        "entry",
        [
            "uv run ruff format --force-exclude --check",
            "uv run ruff format --diff",
            "uv run ruff check --force-exclude",
            "uv run ruff check --no-fix",
            "uv run mypy src/",
            "grep -n TODO file.txt",
        ],
    )
    def test_checking_entry_passes(
        self, overlay: ModelHookWritesOverlay, entry: str
    ) -> None:
        report = _run(overlay, _local(_hook("some-hook", entry)))
        assert report.overall_status == "PASS", report.findings

    def test_args_are_part_of_the_command(
        self, overlay: ModelHookWritesOverlay
    ) -> None:
        source = _local(
            _hook("fmt", "ruff", "        args: [format]\n"),
            _hook("lint", "ruff", "        args: [check, --fix]\n"),
            _hook("lint-ok", "ruff", "        args: [check]\n"),
        )
        report = _run(overlay, source)
        assert len(_fails(report)) == 2
        assert any("fmt" in m for m in _fails(report))
        assert any("lint" in m and "lint-ok" not in m for m in _fails(report))

    def test_temp_dir_writer_is_not_a_tracked_file_writer(
        self, overlay: ModelHookWritesOverlay
    ) -> None:
        entry = (
            'bash -c \'base=$(mktemp -d); trap "rm -rf \\"$base\\"" EXIT; '
            'git archive HEAD .github | tar -x -C "$base"\''
        )
        report = _run(overlay, _local(_hook("temp-only", entry)))
        assert report.overall_status == "PASS", report.findings


class TestWritingHookIds:
    @pytest.mark.parametrize(
        "hook_id", ["end-of-file-fixer", "trailing-whitespace", "yamlfmt"]
    )
    def test_known_rewriting_remote_hook_fails(
        self, overlay: ModelHookWritesOverlay, hook_id: str
    ) -> None:
        source = (
            "repos:\n  - repo: https://example.invalid/hooks\n    rev: v1\n"
            f"    hooks:\n      - id: {hook_id}\n"
        )
        report = _run(overlay, source)
        assert report.overall_status == "FAIL"
        assert hook_id in _fails(report)[0]

    def test_known_rewriting_hook_with_check_only_args_passes(
        self, overlay: ModelHookWritesOverlay
    ) -> None:
        source = (
            "repos:\n  - repo: https://example.invalid/hooks\n    rev: v1\n"
            "    hooks:\n      - id: yamlfmt\n        args: [-lint]\n"
        )
        assert _run(overlay, source).overall_status == "PASS"

    def test_unknown_remote_hook_passes(self, overlay: ModelHookWritesOverlay) -> None:
        source = (
            "repos:\n  - repo: https://example.invalid/hooks\n    rev: v1\n"
            "    hooks:\n      - id: check-merge-conflict\n"
        )
        assert _run(overlay, source).overall_status == "PASS"


class TestFileShapes:
    def test_exported_hook_list_is_read(self, overlay: ModelHookWritesOverlay) -> None:
        source = (
            "- id: exported-writer\n  entry: perl -i -pe 's/a/b/'\n  language: system\n"
            "- id: exported-checker\n  entry: grep -n x\n  language: system\n"
        )
        report = _run(overlay, source, path=_EXPORTED)
        assert len(_fails(report)) == 1
        assert "exported-writer" in _fails(report)[0]

    def test_location_names_file_and_hook(
        self, overlay: ModelHookWritesOverlay
    ) -> None:
        report = _run(overlay, _local(_hook("bad", "sed -i s/a/b/ f")))
        assert report.findings[0].location == f"{_CONFIG}::bad"
        assert report.findings[0].remediation

    def test_unparseable_config_raises(self, overlay: ModelHookWritesOverlay) -> None:
        with pytest.raises(ModelOnexError):
            _run(overlay, "repos: [unclosed")

    def test_non_mapping_config_raises(self, overlay: ModelHookWritesOverlay) -> None:
        with pytest.raises(ModelOnexError):
            _run(overlay, "just a string")


class TestOverlayModel:
    def test_signal_pattern_must_compile(self) -> None:
        with pytest.raises(ValueError, match="regular expression"):
            ModelHookWritesOverlay.model_validate(
                {"signals": [{"id": "x", "pattern": "(", "reason": "ten chars ok"}]}
            )

    def test_overlay_has_values(self, overlay: ModelHookWritesOverlay) -> None:
        assert overlay.signals
        assert overlay.rewriting_hooks
