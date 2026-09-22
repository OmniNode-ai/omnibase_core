# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for architecture-handshakes/gitignore-baseline.yaml (OMN-12451).

This spec is the machine-readable source of truth for which .gitignore
managed blocks every downstream repo must contain. The T2 validator reads
this file, assembles the verbatim block (start marker → ordered patterns →
end marker), and asserts its presence in each target .gitignore.

These tests lock the schema shape so changes to the spec cannot silently
break the validator. If a test fails here, update the schema version in
the spec file before landing the change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pathspec
import pytest
import yaml
from pathspec.patterns.gitwildmatch import GitWildMatchPattern

SPEC_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "architecture-handshakes"
    / "gitignore-baseline.yaml"
)

# Sections the DoD requires. Extending this list is a backwards-compatible
# change; removing from it is not.
REQUIRED_SECTIONS = {"universal", "python", "public_repo_hygiene"}

REQUIRED_BLOCK_FIELDS = {
    "description",
    "start_marker",
    "end_marker",
    "applies_when",
    "patterns",
}

VALID_APPLIES_WHEN = {"always", "pyproject_toml_present"}

# Patterns the spec must declare per section. These are the exact strings
# specified in OMN-12451; removing or reordering any of them is a breaking
# change (the validator asserts sequence, not just membership).
UNIVERSAL_REQUIRED_PATTERNS = [
    ".env",
    ".env.*",
    "!.env.example",
    ".DS_Store",
    "*.log",
    ".idea/",
    ".vscode/",
    "test-results/",
    "playwright-report/",
]

# OMN-18016 (epic OMN-17992). The agent-state, scratch and workspace-index
# trees that kept landing in PUBLIC repositories.
#
# .onex/ and .onex_state/ are deliberately ABSENT and must stay absent: the
# first is product surface read at runtime by the aislop rule loader, and the
# second is governed by this repo's own OMN-15989 re-include, whose retirement
# is blocked on an operator ruling. A conflicting managed rule would silently
# fight a test-asserted rule. test_public_repo_hygiene_block_does_not_fight_the
# _onex_state_reinclude pins that.
PUBLIC_REPO_HYGIENE_REQUIRED_PATTERNS = [
    ".claude/*",
    "!.claude/architecture-handshake.md",
    ".claude_scratch/",
    ".repowise-workspace/",
    ".repowise-workspace.yaml",
    ".evidence/",
    "docs/evidence/",
    # Root-anchored (OMN-18364). See
    # test_hygiene_block_does_not_ignore_nested_packaged_source below for why.
    "/merge-sweep/",
]

PYTHON_REQUIRED_PATTERNS = [
    "__pycache__/",
    "*.py[cod]",
    "*$py.class",
    "/.venv/",
    "/venv/",
    "/env/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".coverage",
    "htmlcov/",
    "dist/",
    "build/",
    "*.egg-info/",
]


@pytest.fixture(scope="module")
def spec() -> dict[str, Any]:
    assert SPEC_PATH.exists(), f"gitignore-baseline.yaml missing at {SPEC_PATH}"
    with SPEC_PATH.open() as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict), "spec root must be a mapping"
    return data


def test_top_level_schema_shape(spec: dict[str, Any]) -> None:
    """Spec file has the top-level keys the validator expects."""
    required = {"schema_version", "managed_blocks", "metadata"}
    assert required <= set(spec.keys()), (
        f"missing top-level keys: {required - set(spec.keys())}"
    )


def test_schema_version_is_semver(spec: dict[str, Any]) -> None:
    """schema_version uses major/minor/patch mapping per ONEX convention."""
    version = spec["schema_version"]
    assert isinstance(version, dict), (
        f"schema_version must be a mapping, got {type(version).__name__}"
    )
    assert set(version.keys()) == {"major", "minor", "patch"}, (
        f"schema_version keys must be {{major, minor, patch}}, got {set(version.keys())}"
    )
    for key, value in version.items():
        assert isinstance(value, int) and value >= 0, (
            f"schema_version.{key} must be a non-negative int, got {value!r}"
        )


def test_required_sections_present(spec: dict[str, Any]) -> None:
    """Both 'universal' and 'python' blocks must be declared."""
    blocks = spec["managed_blocks"]
    assert isinstance(blocks, dict), "managed_blocks must be a mapping"
    missing = REQUIRED_SECTIONS - set(blocks.keys())
    assert not missing, f"managed_blocks missing required sections: {missing}"


def test_every_block_has_required_fields(spec: dict[str, Any]) -> None:
    """Each managed block declares all fields the validator reads."""
    missing: dict[str, set[str]] = {}
    for name, block in spec["managed_blocks"].items():
        gap = REQUIRED_BLOCK_FIELDS - set(block.keys())
        if gap:
            missing[name] = gap
    assert not missing, f"managed blocks missing fields: {missing}"


def test_applies_when_is_valid(spec: dict[str, Any]) -> None:
    """applies_when must be one of the known discriminator values."""
    for name, block in spec["managed_blocks"].items():
        value = block["applies_when"]
        assert value in VALID_APPLIES_WHEN, (
            f"{name}.applies_when must be one of {VALID_APPLIES_WHEN}, got {value!r}"
        )


def test_universal_applies_always(spec: dict[str, Any]) -> None:
    """Universal block must apply to every repo (no pyproject.toml gate)."""
    assert spec["managed_blocks"]["universal"]["applies_when"] == "always"


def test_python_applies_when_pyproject_toml_present(spec: dict[str, Any]) -> None:
    """Python block is gated on pyproject.toml presence."""
    assert spec["managed_blocks"]["python"]["applies_when"] == "pyproject_toml_present"


def test_markers_are_non_empty_strings(spec: dict[str, Any]) -> None:
    for name, block in spec["managed_blocks"].items():
        for marker_field in ("start_marker", "end_marker"):
            value = block[marker_field]
            assert isinstance(value, str) and value.strip(), (
                f"{name}.{marker_field} must be a non-empty string, got {value!r}"
            )


def test_patterns_are_ordered_lists_of_strings(spec: dict[str, Any]) -> None:
    for name, block in spec["managed_blocks"].items():
        patterns = block["patterns"]
        assert isinstance(patterns, list), f"{name}.patterns must be a list"
        assert len(patterns) > 0, f"{name}.patterns must not be empty"
        for pat in patterns:
            assert isinstance(pat, str), (
                f"{name}.patterns entries must be strings, got {type(pat).__name__!r}"
            )


def test_universal_contains_required_patterns_in_order(spec: dict[str, Any]) -> None:
    """Universal block contains exactly the OMN-12451 specified patterns in order.

    Sequence matters — the T2 validator assembles a verbatim block and asserts
    presence. Any reordering is a breaking change.
    """
    patterns = spec["managed_blocks"]["universal"]["patterns"]
    assert patterns == UNIVERSAL_REQUIRED_PATTERNS, (
        f"universal patterns diverge from OMN-12451 spec.\n"
        f"  expected: {UNIVERSAL_REQUIRED_PATTERNS}\n"
        f"  actual:   {patterns}"
    )


def test_python_contains_required_patterns_in_order(spec: dict[str, Any]) -> None:
    """Python block contains exactly the OMN-12451 specified patterns in order."""
    patterns = spec["managed_blocks"]["python"]["patterns"]
    assert patterns == PYTHON_REQUIRED_PATTERNS, (
        f"python patterns diverge from OMN-12451 spec.\n"
        f"  expected: {PYTHON_REQUIRED_PATTERNS}\n"
        f"  actual:   {patterns}"
    )


def test_markers_follow_onex_convention(spec: dict[str, Any]) -> None:
    """Markers must follow the '# === onex-managed: <name> ===' convention."""
    for name, block in spec["managed_blocks"].items():
        start = block["start_marker"]
        end = block["end_marker"]
        assert start == f"# === onex-managed: {name} ===", (
            f"{name}.start_marker does not follow convention: {start!r}"
        )
        assert end == f"# === end onex-managed: {name} ===", (
            f"{name}.end_marker does not follow convention: {end!r}"
        )


def test_metadata_references_owning_ticket(spec: dict[str, Any]) -> None:
    metadata = spec["metadata"]
    assert isinstance(metadata, dict), "metadata must be a mapping"
    related = metadata.get("related_tickets", [])
    assert "OMN-12451" in related, (
        "metadata.related_tickets must include OMN-12451 (this spec's owner ticket)"
    )


# ---------------------------------------------------------------------------
# OMN-18016 — the public-repo hygiene managed block (epic OMN-17992).
# ---------------------------------------------------------------------------


def test_public_repo_hygiene_contains_required_patterns_in_order(
    spec: dict[str, Any],
) -> None:
    """The hygiene block carries exactly the OMN-18016 patterns, in order."""
    patterns = spec["managed_blocks"]["public_repo_hygiene"]["patterns"]
    assert patterns == PUBLIC_REPO_HYGIENE_REQUIRED_PATTERNS, (
        f"public_repo_hygiene patterns diverge from the OMN-18016 spec.\n"
        f"  expected: {PUBLIC_REPO_HYGIENE_REQUIRED_PATTERNS}\n"
        f"  actual:   {patterns}"
    )


def test_public_repo_hygiene_block_does_not_fight_the_onex_state_reinclude(
    spec: dict[str, Any],
) -> None:
    """``.onex_state/`` must stay OUT of the managed block.

    This repo's own ``.gitignore`` deliberately re-includes
    ``.onex_state/evidence/`` and ``.onex_state/friction/`` (OMN-15989), with
    ``test_onex_state_disposable_gitignore.py`` asserting it. Retiring that
    re-include is root cause 4.1 of the OMN-17992 plan and is blocked on an
    operator ruling about the public evidence corpus.

    A managed ``.onex_state/`` rule would be appended AFTER those lines and
    would silently override a test-asserted rule in one repo while reading as
    a fleet-wide hygiene improvement. That is worse than the gap it closes,
    so it is pinned absent until the ruling lands.
    """
    patterns = spec["managed_blocks"]["public_repo_hygiene"]["patterns"]
    offenders = [p for p in patterns if ".onex_state" in p]
    assert not offenders, (
        f"the managed hygiene block declares {offenders}, which fights the "
        "OMN-15989 re-include this repo still asserts. Retire the re-include "
        "first (root cause 4.1), then add the pattern."
    )


def test_public_repo_hygiene_block_does_not_ignore_product_surface(
    spec: dict[str, Any],
) -> None:
    """``.onex/`` is read at runtime by the aislop rule loader, not scratch.

    Ignoring it would break the per-repo override mechanism OMN-11132 shipped,
    and would do it in a change whose stated purpose is hygiene.
    """
    patterns = spec["managed_blocks"]["public_repo_hygiene"]["patterns"]
    offenders = [p for p in patterns if p.rstrip("/*") == ".onex"]
    assert not offenders, (
        f"the managed hygiene block declares {offenders}; .onex/ is product "
        "surface read by the aislop rule loader, not machine state."
    )


def test_the_tracked_handshake_file_survives_the_claude_rule(
    spec: dict[str, Any],
) -> None:
    """A bare ``.claude/*`` would untrack the architecture handshake.

    Every governed repo tracks ``.claude/architecture-handshake.md``. The
    ignore-with-explicit-allowlist-exception pattern is the reason this block
    can ship without breaking the handshake check in eight repos at once.
    """
    patterns = spec["managed_blocks"]["public_repo_hygiene"]["patterns"]
    assert ".claude/*" in patterns
    exception_index = patterns.index("!.claude/architecture-handshake.md")
    assert exception_index > patterns.index(".claude/*"), (
        "the re-include must come AFTER the ignore rule; git applies the last "
        "matching pattern, so an exception placed first does nothing"
    )


def test_metadata_references_the_hygiene_ticket(spec: dict[str, Any]) -> None:
    related = spec["metadata"].get("related_tickets", [])
    assert "OMN-18016" in related, (
        "metadata.related_tickets must name the ticket that added the block"
    )


# ---------------------------------------------------------------------------
# OMN-18859: a bare directory pattern matches at ANY depth, so it can swallow
# a real, tracked package directory and silently drop it from a git-stripped
# wheel build. This has now happened twice through this one spec.
# ---------------------------------------------------------------------------

# Directory patterns that are DELIBERATELY unanchored, each because the thing
# it names is a tooling artifact that legitimately appears at any depth and
# never names a real package directory. An entry here is a reviewed decision,
# not a waiver: adding one is how a future author says "this word cannot
# collide with source", and a reviewer can disagree.
#
# Everything else must be root-anchored. The two incidents both involved a
# plain English word with no leading dot -- exactly the shape most likely to
# also name a real directory inside src/.
DEPTH_MATCHING_BY_DESIGN = {
    # CPython bytecode caches; hatchling prunes these structurally anyway.
    "__pycache__/",
    # Tool caches, always dot-prefixed, never importable package names.
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".idea/",
    ".vscode/",
    ".claude_scratch/",
    ".repowise-workspace/",
    ".evidence/",
    # Coverage HTML output.
    "htmlcov/",
    # Build outputs. A package directory literally named build/ or dist/
    # would itself be a defect, and these must be caught at any depth
    # because a nested sub-project produces them in its own subtree.
    "dist/",
    "build/",
    # Test-runner outputs, produced wherever the runner is invoked.
    "test-results/",
    "playwright-report/",
}


def _directory_patterns(spec: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (section, pattern) for every directory pattern in the spec.

    A directory pattern is one ending in ``/``. Negations (``!``) and
    wildcard patterns (``*.egg-info/``) are excluded: a negation re-includes
    rather than excludes, and a wildcard directory pattern is depth-matching
    by construction -- anchoring it would change what it means rather than
    where it applies.
    """
    out: list[tuple[str, str]] = []
    for section, block in spec["managed_blocks"].items():
        for pattern in block["patterns"]:
            if not pattern.endswith("/"):
                continue
            if pattern.startswith("!") or "*" in pattern:
                continue
            out.append((section, pattern))
    return out


def test_every_plain_directory_pattern_is_root_anchored(spec: dict[str, Any]) -> None:
    """RED before the OMN-18859 fix, GREEN after.

    A bare ``merge-sweep/`` matched this repo family's real, git-tracked
    ``src/omnimarket/adapters/codex/skills/merge-sweep/`` package directory.
    ``stage_workspace.sh`` stages siblings without ``.git``, and hatchling
    applies ``.gitignore`` as an exclude filter regardless of whether ``.git``
    is present, so the tracked ``SKILL.md`` under it was dropped from the
    wheel while the staged source kept it. The OMN-14631 content-parity gate
    then correctly reported the wheel as drifted, and every
    ``BUILD_SOURCE=workspace`` build on the .201 dev lane failed.

    This is the SECOND time. The first was a bare ``env/`` colliding with
    ``omnibase_compat``'s real ``src/omnibase_compat/env/`` submodule, fixed
    by anchoring ``/.venv/``, ``/venv/`` and ``/env/`` -- but only those
    three, which is why it recurred. A third occurrence is now a red test
    here rather than a live-lane outage found by hand.
    """
    unanchored = [
        (section, pattern)
        for section, pattern in _directory_patterns(spec)
        if not pattern.startswith("/")
        and "/" not in pattern[:-1]
        and pattern not in DEPTH_MATCHING_BY_DESIGN
    ]
    assert not unanchored, (
        "these directory patterns are unanchored, so they match a directory of "
        f"that name at ANY depth and can swallow a real package directory: "
        f"{unanchored}. Anchor each to '/<name>/', or, if the name genuinely "
        "cannot collide with source, add it to DEPTH_MATCHING_BY_DESIGN with a "
        "reason (OMN-18859)."
    )


def test_the_allowlist_only_names_patterns_the_spec_declares(
    spec: dict[str, Any],
) -> None:
    """The allowlist must not accumulate entries for patterns that are gone.

    A stale entry silently re-permits an unanchored pattern if that name is
    ever reintroduced, which would defeat the test above without anyone
    editing it.
    """
    declared = {pattern for _section, pattern in _directory_patterns(spec)}
    stale = sorted(DEPTH_MATCHING_BY_DESIGN - declared)
    assert not stale, (
        f"DEPTH_MATCHING_BY_DESIGN names patterns the spec no longer declares: "
        f"{stale}. Remove them so the exemption cannot silently return."
    )


def test_the_hygiene_block_anchors_merge_sweep(spec: dict[str, Any]) -> None:
    """The specific regression, pinned by name (OMN-18859).

    Positive control for the generic test above: if someone reverts the
    anchor while also adding ``merge-sweep/`` to the allowlist, the generic
    test would go quiet and this one would not.
    """
    patterns = spec["managed_blocks"]["public_repo_hygiene"]["patterns"]
    assert "/merge-sweep/" in patterns, (
        "the hygiene block must anchor the merge-sweep rule to the repo root; "
        "a bare 'merge-sweep/' matches omnimarket's real "
        "src/omnimarket/adapters/codex/skills/merge-sweep/ package directory "
        "and drops it from the wheel (OMN-18859)"
    )
    assert "merge-sweep/" not in patterns, (
        "the unanchored form must not be declared alongside the anchored one"
    )


# ---------------------------------------------------------------------------
# OMN-18364 — the hygiene block's directory patterns must be root-anchored.
# ---------------------------------------------------------------------------

# The shape that broke: omnimarket ships an agent skill as PACKAGED SOURCE at
# src/omnimarket/adapters/codex/skills/merge-sweep/SKILL.md. It is tracked, it
# is part of the wheel, and it is nested — not repo-root scratch.
_NESTED_PACKAGED_SOURCE_PATH = (
    "src/omnimarket/adapters/codex/skills/merge-sweep/SKILL.md"
)

# The shape the block is actually FOR: repo-root agent scratch.
_ROOT_SCRATCH_PATHS = [
    "merge-sweep/run-2026-09-19.json",
    "merge-sweep/state.db",
]


def _hygiene_spec(spec: dict[str, Any]) -> pathspec.PathSpec:
    """Compile the shipped hygiene patterns with git's own wildmatch dialect."""
    patterns = spec["managed_blocks"]["public_repo_hygiene"]["patterns"]
    return pathspec.PathSpec.from_lines(GitWildMatchPattern, patterns)


def test_hygiene_block_does_not_ignore_nested_packaged_source(
    spec: dict[str, Any],
) -> None:
    """A nested packaged ``merge-sweep/`` source dir must NOT be ignored.

    Measured regression (OMN-18364, 2026-09-19): the block shipped
    ``merge-sweep/`` unanchored, which git matches at ANY depth. omnimarket
    adopted the managed block in omnimarket#2670 (commit 61187c8c1) and its
    tracked ``src/omnimarket/adapters/codex/skills/merge-sweep/SKILL.md``
    became VCS-ignored. Hatchling excludes VCS-ignored files from the wheel,
    so the file was present in the staged source tree and absent from the
    built wheel, and the OMN-14631 workspace content-parity gate hard-failed
    every ``BUILD_SOURCE=workspace`` runtime image build with
    ``INSTALLED CONTENT DRIFT for 'omnimarket'``. That blocked
    ``deliver-dev-candidate-to-staging`` run 35473178811.

    Same failure class as the OMN-14636 ``/env/`` root-anchoring fix in the
    python block. Do not un-anchor this pattern.
    """
    matched = _hygiene_spec(spec).match_file(_NESTED_PACKAGED_SOURCE_PATH)
    assert not matched, (
        f"the public_repo_hygiene block ignores {_NESTED_PACKAGED_SOURCE_PATH!r}, "
        "a nested packaged source path. Some directory pattern in the block is "
        "unanchored and is matching at depth; root-anchor it with a leading "
        "slash (OMN-18364)."
    )


def test_hygiene_block_still_ignores_repo_root_merge_sweep(
    spec: dict[str, Any],
) -> None:
    """Positive control: the block keeps its repo-root hygiene intent.

    Without this, the test above would pass just as well if the pattern were
    deleted outright, which is not the fix.
    """
    compiled = _hygiene_spec(spec)
    for path in _ROOT_SCRATCH_PATHS:
        assert compiled.match_file(path), (
            f"the public_repo_hygiene block no longer ignores {path!r}. "
            "Root-anchoring the pattern must not delete its hygiene intent "
            "(OMN-18364)."
        )


def test_hygiene_dotless_directory_patterns_are_root_anchored(
    spec: dict[str, Any],
) -> None:
    """Every plain, dot-less directory pattern carries a leading slash.

    Scope, stated rather than implied: this asserts over patterns whose name
    does not begin with a dot. A leading dot is not a valid Python identifier,
    so a ``.claude_scratch/``-shaped entry can never be an importable packaged
    source directory and cannot reproduce the OMN-18364 wheel-stripping
    failure; those are left unanchored as shipped. A dot-less ``name/`` can,
    and ``merge-sweep/`` did. Patterns containing a mid-string slash
    (``docs/evidence/``) are already anchored by git's own rule.
    """
    patterns = spec["managed_blocks"]["public_repo_hygiene"]["patterns"]
    offenders = [
        p
        for p in patterns
        if p.endswith("/") and not p.startswith(("/", "!", ".")) and "/" not in p[:-1]
    ]
    assert not offenders, (
        f"unanchored dot-less directory patterns in public_repo_hygiene: "
        f"{offenders}. Each matches a directory of that name at ANY depth and "
        "will strip a nested tracked source directory out of a git-aware "
        "wheel build (OMN-18364)."
    )
