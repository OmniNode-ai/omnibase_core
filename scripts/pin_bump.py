#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cross-repo SHA pin-bump engine (OMN-9050).

Invoked by `.github/workflows/publish-downstream-pin-bump.yml` after an
omnibase_core push to main. Reads `docs/downstream-repos.yaml`, then for each
checked-out downstream repo rewrites every declared pin site to the new SHA
and updates the banner comment so readers know the pin was bot-managed.

Usage (single repo, typically invoked by the workflow):

    uv run python scripts/pin_bump.py \\
        --manifest docs/downstream-repos.yaml \\
        --repo omniclaude \\
        --repo-root /tmp/downstream/omniclaude \\
        --new-sha <40-char-sha>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
BANNER_OLD_RE = re.compile(
    r"#\s*Pinned to omnibase_core[^\n]*\n\s*#\s*Update by running:[^\n]*\n",
    re.MULTILINE,
)
BANNER_ANY_OLD_RE = re.compile(
    r"#\s*(?:Pinned to omnibase_core|Auto-bumped by omnibase_core)[^\n]*\n",
    re.MULTILINE,
)


class PinSite(BaseModel):
    path: str
    pattern: str


class RepoEntry(BaseModel):
    name: str
    owner: str
    pin_sites: list[PinSite] = Field(default_factory=list)
    notes: str | None = None


class PinBumpManifest(BaseModel):
    version: int
    repos: list[RepoEntry]


class BumpResult(BaseModel):
    path: str
    changed: bool
    old_sha: str
    new_sha: str


def load_manifest(path: Path) -> PinBumpManifest:
    raw = yaml.safe_load(path.read_text())
    manifest = PinBumpManifest.model_validate(raw)
    if manifest.version != 1:
        raise ValueError(
            f"unsupported manifest version {manifest.version!r}; this script understands version 1",
        )
    return manifest


def _validate_sha(sha: str) -> None:
    if not SHA_RE.match(sha):
        raise ValueError(f"{sha!r} is not a 40-char lowercase hex SHA")


def _rewrite_banner(content: str, new_sha: str) -> str:
    short = new_sha[:12]
    banner = (
        f"          # Auto-bumped by omnibase_core publish-downstream-pin-bump.yml "
        f"to {short}.\n"
    )
    if BANNER_OLD_RE.search(content):
        return BANNER_OLD_RE.sub(banner, content, count=1)
    if BANNER_ANY_OLD_RE.search(content):
        return BANNER_ANY_OLD_RE.sub(banner, content, count=1)
    return content


def bump_file(repo_root: Path, site: PinSite, new_sha: str) -> BumpResult:
    _validate_sha(new_sha)
    target = repo_root / site.path
    content = target.read_text()
    compiled = re.compile(site.pattern)
    if compiled.groups != 1:
        raise ValueError(
            f"pattern {site.pattern!r} must have exactly one capture group over the SHA"
            f" (has {compiled.groups})",
        )
    m = compiled.search(content)
    if m is None:
        raise ValueError(
            f"no match for pattern {site.pattern!r} in {site.path!r}",
        )
    old_sha = m.group(1)
    if old_sha == new_sha:
        return BumpResult(
            path=site.path, changed=False, old_sha=old_sha, new_sha=new_sha
        )

    start, end = m.span(1)
    updated = content[:start] + new_sha + content[end:]
    updated = _rewrite_banner(updated, new_sha)
    target.write_text(updated)
    return BumpResult(path=site.path, changed=True, old_sha=old_sha, new_sha=new_sha)


def bump_repo(repo_root: Path, entry: RepoEntry, new_sha: str) -> list[BumpResult]:
    return [bump_file(repo_root, site, new_sha) for site in entry.pin_sites]


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Bump omnibase_core SHA pins in a downstream repo."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--repo", required=True, help="repo name (matches manifest 'name' field)"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        required=True,
        help="path to the downstream repo checkout",
    )
    parser.add_argument("--new-sha", required=True)
    args = parser.parse_args(argv)

    manifest = load_manifest(args.manifest)
    entry = next((r for r in manifest.repos if r.name == args.repo), None)
    if entry is None:
        print(f"repo {args.repo!r} is not in {args.manifest}", file=sys.stderr)
        return 2

    results = bump_repo(args.repo_root, entry, args.new_sha)
    for r in results:
        marker = "CHANGED" if r.changed else "unchanged"
        print(f"{marker}: {r.path} ({r.old_sha[:12]} -> {r.new_sha[:12]})")
    if not results:
        print(f"repo {args.repo!r} has no declared pin sites yet; nothing to do.")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
