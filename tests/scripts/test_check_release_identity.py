# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the release-identity gate (OMN-13411).

The gate forbids merging a packaged-source change onto an already-published
version string. It is the omnibase_core port of the omnibase_infra release
identity gate (OMN-13412) and the recurrence guard for the OMN-13402/OMN-13405
"unreleased code on a published version" crash.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest
from packaging.version import Version

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_release_identity.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_release_identity", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def mod():
    return _load_module()


@pytest.mark.unit
def test_passes_when_version_ahead_of_published(mod, monkeypatch):
    """src/** changed, but the version is strictly ahead — gate passes."""
    monkeypatch.setattr(mod, "_read_pyproject_version", lambda: Version("0.46.0"))
    monkeypatch.setattr(mod, "_latest_published_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_packaged_source_changed", lambda base, explicit: True)
    assert mod.main(["--base", "origin/dev"]) == 0


@pytest.mark.unit
def test_fails_when_src_changed_and_version_equals_published(mod, monkeypatch):
    """src/** changed and the version equals the published wheel — gate FAILS.

    This is the literal OMN-13405 footgun: core dev HEAD carried unreleased
    modules while still labelled 0.45.0 (== the published wheel).
    """
    monkeypatch.setattr(mod, "_read_pyproject_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_latest_published_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_packaged_source_changed", lambda base, explicit: True)
    assert mod.main(["--base", "origin/dev"]) == 1


@pytest.mark.unit
def test_fails_when_src_changed_and_version_behind_published(mod, monkeypatch):
    """A version BEHIND the latest published tag is also a fail."""
    monkeypatch.setattr(mod, "_read_pyproject_version", lambda: Version("0.44.0"))
    monkeypatch.setattr(mod, "_latest_published_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_packaged_source_changed", lambda base, explicit: True)
    assert mod.main(["--base", "origin/dev"]) == 1


@pytest.mark.unit
def test_exempt_when_no_packaged_source_changed(mod, monkeypatch):
    """A docs/tests/CI-only diff is exempt — the published wheel is unaffected."""
    monkeypatch.setattr(mod, "_read_pyproject_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_latest_published_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_packaged_source_changed", lambda base, explicit: False)
    assert mod.main(["--base", "origin/dev"]) == 0


@pytest.mark.unit
def test_passes_when_no_published_tag_yet(mod, monkeypatch):
    """A repo with no published tags cannot alias a published version."""
    monkeypatch.setattr(mod, "_read_pyproject_version", lambda: Version("0.1.0"))
    monkeypatch.setattr(mod, "_latest_published_version", lambda: None)
    assert mod.main(["--base", "origin/dev"]) == 0


@pytest.mark.unit
def test_config_error_on_missing_version(mod, monkeypatch):
    """A missing project.version is a config error (exit 2), not a pass."""

    def _raise():
        raise ValueError("no project.version")

    monkeypatch.setattr(mod, "_read_pyproject_version", _raise)
    assert mod.main(["--base", "origin/dev"]) == 2


@pytest.mark.unit
def test_packaged_source_changed_detects_src_prefix(mod):
    """The src/ prefix triggers the bump requirement; non-src does not."""
    assert mod._packaged_source_changed(None, ["src/omnibase_core/enums/enum_x.py"])
    assert not mod._packaged_source_changed(
        None, ["docs/foo.md", "tests/test_x.py", ".github/workflows/ci.yml"]
    )


@pytest.mark.unit
def test_explicit_changed_file_overrides_base(mod, monkeypatch):
    """An explicit --changed-file list bypasses git diffing entirely."""
    monkeypatch.setattr(mod, "_read_pyproject_version", lambda: Version("0.45.0"))
    monkeypatch.setattr(mod, "_latest_published_version", lambda: Version("0.45.0"))
    # Explicit src file => changed => must be ahead => fails at 0.45.0.
    assert mod.main(["--changed-file", "src/omnibase_core/foo.py"]) == 1
    # Explicit docs file => not changed => exempt => passes.
    assert mod.main(["--changed-file", "docs/foo.md"]) == 0


@pytest.mark.unit
def test_live_invocation_smoke():
    """Real subprocess run against the actual repo must succeed (version ahead).

    The subprocess sees a local published-version tag regardless of checkout tag
    depth, so the strict-mode run proves the script is importable and wired
    correctly end to end.
    """
    repo = _SCRIPT.resolve().parents[1]
    smoke_tag = "v0.45.999999"
    subprocess.run(["git", "tag", "-f", smoke_tag, "HEAD"], cwd=repo, check=True)
    try:
        result = subprocess.run(
            ["python", str(_SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo,
        )
        assert result.returncode == 0, result.stderr
        assert "ahead of latest published" in result.stdout
    finally:
        subprocess.run(["git", "tag", "-d", smoke_tag], cwd=repo, check=False)
