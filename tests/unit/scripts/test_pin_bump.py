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

OLD_SHA = "330a344cdb9c5dedd04a46dfbb0b63dae0baccfb"  # pragma: allowlist secret
NEW_SHA = "abcdef0123456789abcdef0123456789abcdef01"  # pragma: allowlist secret


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


# --- Regression coverage for the env-var-indirection pin shape (OMN-19848) ---
#
# omninode_infra's check-handshake.yml moved from an inline `ref: <sha>` to an
# env-var indirection (`OMNIBASE_CORE_COMMIT: <sha>` at the job/env level, then
# `ref: ${{ env.OMNIBASE_CORE_COMMIT }}` at the checkout step). The manifest's
# pin_sites pattern for omninode_infra was never updated to match, so every
# publish-downstream-pin-bump.yml run since has raised ValueError instead of
# bumping the pin (docs/tracking/ROLLING_WORK_LEDGER.md FRICTION row,
# lane omninode-infra-core-bump-83, 2026-09-27T03:30:12Z).


def _make_env_var_indirection_handshake(root: Path, sha: str) -> Path:
    """Reproduce omninode_infra's actual check-handshake.yml pin shape."""
    p = root / ".github" / "workflows" / "check-handshake.yml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "name: Check Architecture Handshake\n"
        "env:\n"
        "  # Pinned to omnibase_core main as of 2026-02-09.\n"
        "  # Update by running: gh api repos/OmniNode-ai/omnibase_core/commits/main --jq '.sha'\n"
        f"  OMNIBASE_CORE_COMMIT: {sha}\n"
        "jobs:\n"
        "  check-handshake:\n"
        "    steps:\n"
        "      - name: Checkout omnibase_core\n"
        "        uses: actions/checkout@v6\n"
        "        with:\n"
        "          repository: OmniNode-ai/omnibase_core\n"
        "          ref: ${{ env.OMNIBASE_CORE_COMMIT }}\n"
        "          path: omnibase_core\n"
    )
    return p


def test_bump_file_matches_env_var_indirection_pattern(tmp_repo: Path) -> None:
    """Positive: the corrected pattern matches the OMNIBASE_CORE_COMMIT line."""
    f = _make_env_var_indirection_handshake(tmp_repo, OLD_SHA)
    site = PinSite(
        path=str(f.relative_to(tmp_repo)),
        pattern=r"OMNIBASE_CORE_COMMIT:\s*([0-9a-f]{40})",
    )
    result = bump_file(tmp_repo, site, NEW_SHA)
    assert result.changed is True
    assert result.old_sha == OLD_SHA
    content = f.read_text()
    assert f"OMNIBASE_CORE_COMMIT: {NEW_SHA}" in content
    # the literal-ref checkout line is untouched (it's an expression, not a SHA)
    assert "ref: ${{ env.OMNIBASE_CORE_COMMIT }}" in content


def test_bump_file_raises_on_stale_ref_pattern_against_env_var_indirection(
    tmp_repo: Path,
) -> None:
    """Negative regression: the OLD (pre-fix) manifest pattern must fail loudly,
    not silently no-op, against the env-var-indirection shape — this is the
    exact ValueError every publish-downstream-pin-bump.yml run hit."""
    f = _make_env_var_indirection_handshake(tmp_repo, OLD_SHA)
    site = PinSite(path=str(f.relative_to(tmp_repo)), pattern=r"ref:\s*([0-9a-f]{40})")
    with pytest.raises(ValueError, match="no match"):
        bump_file(tmp_repo, site, NEW_SHA)


def test_shipped_manifest_omninode_infra_pattern_matches_its_own_pin_shape(
    tmp_repo: Path,
) -> None:
    """Guards the actual docs/downstream-repos.yaml entry: omninode_infra pins via
    OMNIBASE_CORE_COMMIT env-var indirection, not an inline `ref: <sha>`, so the
    manifest's declared pattern for it must match that shape. Fails RED against
    the pre-fix manifest pattern `ref:\\s*([0-9a-f]{40})`."""
    manifest_path = (
        Path(__file__).parent.parent.parent.parent / "docs" / "downstream-repos.yaml"
    )
    manifest = load_manifest(manifest_path)
    entry = next(r for r in manifest.repos if r.name == "omninode_infra")
    site = next(
        s for s in entry.pin_sites if s.path == ".github/workflows/check-handshake.yml"
    )

    f = _make_env_var_indirection_handshake(tmp_repo, OLD_SHA)
    result = bump_file(
        tmp_repo,
        PinSite(path=str(f.relative_to(tmp_repo)), pattern=site.pattern),
        NEW_SHA,
    )
    assert result.changed is True
    assert result.old_sha == OLD_SHA


# A low-entropy 40-hex ref: a pin of another repository, never an omnibase_core sha.
FOREIGN_SHA = "0f" * 20


def _make_ci_with_foreign_ref(root: Path, *, core_sha: str | None) -> Path:
    """A ci.yml shape like omniclaude's: onex_change_control checkouts pin a ref,
    the omnibase_core checkout may or may not."""
    p = root / ".github" / "workflows" / "ci.yml"
    p.parent.mkdir(parents=True, exist_ok=True)
    core_ref = f"          ref: {core_sha}\n" if core_sha else ""
    p.write_text(
        "jobs:\n"
        "  gate:\n"
        "    steps:\n"
        "      - name: Checkout onex_change_control validator\n"
        "        uses: actions/checkout@v7\n"
        "        with:\n"
        "          repository: OmniNode-ai/onex_change_control\n"
        f"          ref: {FOREIGN_SHA}\n"
        "          path: onex_change_control\n"
        "      - name: Checkout omnibase_core\n"
        "        uses: actions/checkout@v7\n"
        "        with:\n"
        "          repository: OmniNode-ai/omnibase_core\n"
        f"{core_ref}"
        "          path: omnibase_core\n"
    )
    return p


def test_bump_file_foreign_repository_ref_is_untouched(tmp_repo: Path) -> None:
    f = _make_ci_with_foreign_ref(tmp_repo, core_sha=OLD_SHA)
    site = PinSite(path=str(f.relative_to(tmp_repo)), pattern=r"ref:\s*([0-9a-f]{40})")
    result = bump_file(tmp_repo, site, NEW_SHA)
    content = f.read_text()
    assert result.old_sha == OLD_SHA
    assert FOREIGN_SHA in content
    assert f"ref: {NEW_SHA}" in content
    assert OLD_SHA not in content


def test_bump_file_foreign_repository_only_raises_and_writes_nothing(
    tmp_repo: Path,
) -> None:
    f = _make_ci_with_foreign_ref(tmp_repo, core_sha=None)
    before = f.read_text()
    site = PinSite(path=str(f.relative_to(tmp_repo)), pattern=r"ref:\s*([0-9a-f]{40})")
    with pytest.raises(ValueError, match="no match"):
        bump_file(tmp_repo, site, NEW_SHA)
    assert f.read_text() == before


def test_shipped_manifest_never_rewrites_a_foreign_ref(tmp_repo: Path) -> None:
    manifest_path = (
        Path(__file__).parent.parent.parent.parent / "docs" / "downstream-repos.yaml"
    )
    manifest = load_manifest(manifest_path)
    for entry in manifest.repos:
        for site in entry.pin_sites:
            f = _make_ci_with_foreign_ref(tmp_repo, core_sha=OLD_SHA)
            target = tmp_repo / site.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f.read_text())
            try:
                bump_file(tmp_repo, site, NEW_SHA)
            except ValueError:
                pass  # shape of this file is not the ci.yml shape; nothing written
            assert FOREIGN_SHA in target.read_text(), (entry.name, site.path)


def test_shipped_manifest_omniclaude_ci_yml_is_not_a_pin_site() -> None:
    """omniclaude ci.yml holds no omnibase_core ref pin; declaring it made the bot
    rewrite an onex_change_control ref (omniclaude#2458)."""
    manifest_path = (
        Path(__file__).parent.parent.parent.parent / "docs" / "downstream-repos.yaml"
    )
    manifest = load_manifest(manifest_path)
    entry = next(r for r in manifest.repos if r.name == "omniclaude")
    assert [s.path for s in entry.pin_sites] == [
        ".github/workflows/check-handshake.yml"
    ]


def test_shipped_manifest_omnidash_onex_schema_compat_is_not_a_pin_site() -> None:
    """omnidash onex-schema-compat.yml pins onex_change_control, not omnibase_core."""
    manifest_path = (
        Path(__file__).parent.parent.parent.parent / "docs" / "downstream-repos.yaml"
    )
    manifest = load_manifest(manifest_path)
    entry = next(r for r in manifest.repos if r.name == "omnidash")
    assert ".github/workflows/onex-schema-compat.yml" not in [
        s.path for s in entry.pin_sites
    ]
