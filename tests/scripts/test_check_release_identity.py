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
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from packaging.version import Version

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

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


def _isolated_checkout(tmp_path: Path, *, published_tag: str) -> Path:
    """Stand the REAL script up in a throwaway repo whose tag set we own.

    ``check_release_identity`` derives its repo root from its own file location
    (``Path(__file__).resolve().parents[1]``) and shells out to ``git`` there,
    so copying the real script + the real ``pyproject.toml`` into
    ``<tmp>/scripts/`` + ``<tmp>/`` makes ``<tmp>`` the root it inspects. Every
    input the gate reads is then under the test's control -- no tags are
    written into, or deleted from, the developer's actual checkout.
    """
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    shutil.copy2(_SCRIPT, root / "scripts" / _SCRIPT.name)
    shutil.copy2(
        _SCRIPT.resolve().parents[1] / "pyproject.toml", root / "pyproject.toml"
    )

    # Must stay named `scrubbed_git_env`: no_unguarded_git_subprocess keys on a
    # canonical scrub name appearing in the `env=` expression itself, so a
    # differently-named local reads as an unscrubbed ambient env and fails
    # closed -- which is exactly what it did to the first cut of this helper.
    scrubbed_git_env = scrub_git_location_env(os.environ)
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "smoke"],
        ["tag", published_tag],
    ):
        subprocess.run(["git", *args], cwd=root, check=True, env=scrubbed_git_env)
    return root


def _run_gate(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the gate against ``root`` only.

    The scrub is load-bearing, not ceremony: GIT_DIR / GIT_WORK_TREE override
    ``cwd``, so an ambient one (a git hook exports exactly these -- the
    OMN-14891 case) would make the gate's internal ``git tag --list`` read the
    developer's real checkout instead of the isolated repo, and the isolation
    this whole helper exists to provide would silently evaporate.
    """
    scrubbed_git_env = scrub_git_location_env(os.environ)
    return subprocess.run(
        [sys.executable, str(root / "scripts" / _SCRIPT.name)],
        capture_output=True,
        text=True,
        check=False,
        cwd=root,
        env=scrubbed_git_env,
    )


@pytest.mark.unit
def test_live_invocation_smoke(tmp_path):
    """Real subprocess run of the real script, end to end: version ahead => 0.

    OMN-15603: this smoke used to force a ``v0.45.999999`` tag into the ACTUAL
    repo and assert strict mode exited 0. That fixture was version-fragile by
    construction -- ``_latest_published_version`` takes the MAX over all tags,
    so the synthetic tag only decides the comparison while it outranks every
    real tag. Once ``v0.46.x`` was cut the synthetic tag went inert, the real
    tag became the maximum, and the assertion inverted: with dev's
    ``project.version`` equal to the newest tag (the normal state of the tree
    in the whole window between a release and the next bump) strict mode
    correctly exits 1 and this test failed on every open PR. The gate was
    right; the fixture was wrong. Owning the tag set outright fixes it for
    good, and drops the mutate-then-restore dance on the real checkout that
    OMN-14891 had to harden.
    """
    root = _isolated_checkout(tmp_path, published_tag="v0.0.1")

    result = _run_gate(root)

    assert result.returncode == 0, result.stderr
    assert "ahead of latest published" in result.stdout


@pytest.mark.unit
def test_live_invocation_fails_when_version_is_not_ahead(tmp_path):
    """Live negative: the gate must FAIL, not merely be absent, when behind.

    Exists-but-wrong, end to end through the real subprocess -- a script that
    silently exited 0 on an un-bumped version would pass the positive smoke
    above and still let the OMN-13405 footgun through.
    """
    root = _isolated_checkout(tmp_path, published_tag="v99.0.0")

    result = _run_gate(root)

    assert result.returncode == 1, result.stdout
    assert "is NOT ahead of the latest published version" in result.stderr
