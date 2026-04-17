# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for scripts/pin_bump.py — cross-repo SHA pin-bump engine (OMN-9050).

Covers:
1. Manifest parsing (PinBumpManifest / PinSite / RepoEntry models).
2. SHA rewrite in a file with one capture group (idempotent).
3. Multiple pin sites in one repo.
4. No-op when the file already contains the target SHA.
5. Error when the pattern matches zero or >1 groups, or no line in file.
6. Comment banner update ("Auto-bumped by ...") on check-handshake.yml.
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))

from pin_bump import (  # type: ignore[import-not-found]
    BumpResult,
    PinBumpManifest,
    PinSite,
    RepoEntry,
    bump_file,
    bump_repo,
    load_manifest,
)

OLD_SHA = "330a344cdb9c5dedd04a46dfbb0b63dae0baccfb"
NEW_SHA = "abcdef0123456789abcdef0123456789abcdef01"


@pytest.fixture
def tmp_repo() -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def manifest_text() -> str:
    return """
version: 1
repos:
  - name: omniclaude
    owner: OmniNode-ai
    pin_sites:
      - path: .github/workflows/check-handshake.yml
        pattern: "ref:\\\\s*([0-9a-f]{40})"
"""


def _make_handshake(root: Path, sha: str) -> Path:
    p = root / ".github" / "workflows" / "check-handshake.yml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "name: Check Architecture Handshake\n"
        "jobs:\n"
        "  check-handshake:\n"
        "    steps:\n"
        "      - uses: actions/checkout@v6\n"
        "        with:\n"
        "          repository: OmniNode-ai/omnibase_core\n"
        f"          # Pinned to omnibase_core main as of 2026-03-22.\n"
        f"          ref: {sha}\n"
        f"          path: omnibase_core\n"
    )
    return p


def test_manifest_parses(tmp_repo: Path, manifest_text: str) -> None:
    mf = tmp_repo / "downstream-repos.yaml"
    mf.write_text(manifest_text)
    manifest = load_manifest(mf)
    assert isinstance(manifest, PinBumpManifest)
    assert manifest.version == 1
    assert len(manifest.repos) == 1
    assert manifest.repos[0].name == "omniclaude"
    assert manifest.repos[0].owner == "OmniNode-ai"
    assert (
        manifest.repos[0].pin_sites[0].path == ".github/workflows/check-handshake.yml"
    )


def test_manifest_rejects_unknown_version(tmp_repo: Path) -> None:
    mf = tmp_repo / "bad.yaml"
    mf.write_text("version: 99\nrepos: []\n")
    with pytest.raises(ValueError, match="manifest version"):
        load_manifest(mf)


def test_bump_file_rewrites_sha(tmp_repo: Path) -> None:
    f = _make_handshake(tmp_repo, OLD_SHA)
    site = PinSite(path=str(f.relative_to(tmp_repo)), pattern=r"ref:\s*([0-9a-f]{40})")
    result = bump_file(tmp_repo, site, NEW_SHA)
    assert result.changed is True
    assert result.old_sha == OLD_SHA
    assert result.new_sha == NEW_SHA
    content = f.read_text()
    assert NEW_SHA in content
    assert OLD_SHA not in content


def test_bump_file_is_idempotent(tmp_repo: Path) -> None:
    f = _make_handshake(tmp_repo, NEW_SHA)
    site = PinSite(path=str(f.relative_to(tmp_repo)), pattern=r"ref:\s*([0-9a-f]{40})")
    result = bump_file(tmp_repo, site, NEW_SHA)
    assert result.changed is False
    assert result.old_sha == NEW_SHA
    assert result.new_sha == NEW_SHA


def test_bump_file_raises_when_pattern_missing(tmp_repo: Path) -> None:
    f = tmp_repo / "empty.yml"
    f.write_text("no sha here\n")
    site = PinSite(path="empty.yml", pattern=r"ref:\s*([0-9a-f]{40})")
    with pytest.raises(ValueError, match="no match"):
        bump_file(tmp_repo, site, NEW_SHA)


def test_bump_file_raises_on_pattern_without_capture_group(tmp_repo: Path) -> None:
    f = _make_handshake(tmp_repo, OLD_SHA)
    site = PinSite(path=str(f.relative_to(tmp_repo)), pattern=r"ref:\s*[0-9a-f]{40}")
    with pytest.raises(ValueError, match="capture group"):
        bump_file(tmp_repo, site, NEW_SHA)


def test_bump_file_updates_banner_comment(tmp_repo: Path) -> None:
    f = _make_handshake(tmp_repo, OLD_SHA)
    site = PinSite(path=str(f.relative_to(tmp_repo)), pattern=r"ref:\s*([0-9a-f]{40})")
    bump_file(tmp_repo, site, NEW_SHA)
    content = f.read_text()
    assert "Auto-bumped by omnibase_core publish-downstream-pin-bump.yml" in content
    assert NEW_SHA[:12] in content
    assert "Pinned to omnibase_core main as of 2026-03-22" not in content


def test_bump_repo_walks_all_sites(tmp_repo: Path) -> None:
    f1 = _make_handshake(tmp_repo, OLD_SHA)
    f2 = tmp_repo / ".github" / "workflows" / "ci.yml"
    f2.parent.mkdir(parents=True, exist_ok=True)
    f2.write_text(f"steps:\n  - uses: x\n    with:\n      ref: {OLD_SHA}\n")
    entry = RepoEntry(
        name="omniclaude",
        owner="OmniNode-ai",
        pin_sites=[
            PinSite(
                path=str(f1.relative_to(tmp_repo)), pattern=r"ref:\s*([0-9a-f]{40})"
            ),
            PinSite(
                path=str(f2.relative_to(tmp_repo)), pattern=r"ref:\s*([0-9a-f]{40})"
            ),
        ],
    )
    results = bump_repo(tmp_repo, entry, NEW_SHA)
    assert len(results) == 2
    assert all(isinstance(r, BumpResult) for r in results)
    assert all(r.changed for r in results)
    assert NEW_SHA in f1.read_text()
    assert NEW_SHA in f2.read_text()


def test_bump_repo_skips_entries_with_no_pin_sites(tmp_repo: Path) -> None:
    entry = RepoEntry(name="omniweb", owner="OmniNode-ai", pin_sites=[])
    results = bump_repo(tmp_repo, entry, NEW_SHA)
    assert results == []


def test_invalid_sha_rejected(tmp_repo: Path) -> None:
    f = _make_handshake(tmp_repo, OLD_SHA)
    site = PinSite(path=str(f.relative_to(tmp_repo)), pattern=r"ref:\s*([0-9a-f]{40})")
    with pytest.raises(ValueError, match="40-char lowercase hex"):
        bump_file(tmp_repo, site, "not-a-sha")
