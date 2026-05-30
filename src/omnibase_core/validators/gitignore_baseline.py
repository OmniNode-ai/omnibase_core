# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""gitignore-baseline validator (OMN-12452).

Reads architecture-handshakes/gitignore-baseline.yaml and asserts that every
governed managed block appears VERBATIM — exact start marker, ordered patterns,
exact end marker — in the target repo's .gitignore.

Block application rules (from the spec):
  - "universal"  : enforced on ALL repos regardless of language or stack.
  - "python"     : enforced only on repos that contain pyproject.toml at root.
  - (future keys): any block whose applies_when is "always" is enforced on all
                   repos; "pyproject_toml_present" gates on that file's presence.

Usage::

    # Validate the current repo root
    python -m omnibase_core.validators.gitignore_baseline .

    # Validate an explicit repo directory
    python -m omnibase_core.validators.gitignore_baseline /path/to/repo

Suppression::

    Add  # gitignore-ok: <reason>  anywhere in the .gitignore file to suppress
    all findings for that file. This is a file-level suppression, not per-line,
    because managed blocks must appear as exact verbatim sequences — a mid-block
    suppression comment would itself corrupt the block.

Exit codes:
  0 — no findings
  1 — one or more findings (details on stderr)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml  # ONEX_EXCLUDE: manual_yaml - validator reads architecture-handshakes spec

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SPEC_RELATIVE_PATH = Path("architecture-handshakes") / "gitignore-baseline.yaml"
_SUPPRESSION_MARKER = "# gitignore-ok:"
_VALIDATOR_NAME = "gitignore_baseline"


# ---------------------------------------------------------------------------
# Spec loading
# ---------------------------------------------------------------------------


def _locate_spec(repo_root: Path) -> Path:
    """Return the absolute path to the gitignore-baseline spec, searching upward."""
    # First: adjacent to the repo root (standard layout for omnibase_core)
    candidate = repo_root / _SPEC_RELATIVE_PATH
    if candidate.exists():
        return candidate

    # Second: the validator lives inside omnibase_core; walk up to find the spec
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        candidate = ancestor / _SPEC_RELATIVE_PATH
        if candidate.exists():
            return candidate

    msg = f"gitignore-baseline.yaml not found. Searched: {repo_root / _SPEC_RELATIVE_PATH} and parents of {here}"
    raise FileNotFoundError(msg)  # error-ok: validator CLI; not a node handler


def _load_spec(spec_path: Path) -> dict[str, object]:
    """Load and return the parsed spec YAML."""
    # ONEX_EXCLUDE: manual_yaml - validator reads architecture-handshakes spec
    data = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        msg = (
            f"gitignore-baseline.yaml root must be a mapping, got {type(data).__name__}"
        )
        raise ValueError(msg)  # error-ok: validator CLI; not a node handler
    return data


# ---------------------------------------------------------------------------
# Block assembly
# ---------------------------------------------------------------------------


def _assemble_block(block: dict[str, object]) -> list[str]:
    """Assemble the ordered verbatim lines for a managed block.

    Returns the list of lines (without trailing newlines) that must appear,
    in order, as a contiguous subsequence inside .gitignore:
      [start_marker, pattern[0], pattern[1], ..., end_marker]
    """
    start: str = block["start_marker"]  # type: ignore[assignment]
    end: str = block["end_marker"]  # type: ignore[assignment]
    patterns: list[str] = block["patterns"]  # type: ignore[assignment]
    return [start, *patterns, end]


# ---------------------------------------------------------------------------
# Detection logic
# ---------------------------------------------------------------------------


def _block_present(gitignore_lines: list[str], block_lines: list[str]) -> bool:
    """Return True if block_lines appears as a contiguous verbatim subsequence.

    Comparison strips trailing whitespace from each line but is otherwise exact.
    """
    if not block_lines:
        return True
    stripped_gitignore = [ln.rstrip() for ln in gitignore_lines]
    stripped_block = [ln.rstrip() for ln in block_lines]
    needle_len = len(stripped_block)
    for i in range(len(stripped_gitignore) - needle_len + 1):
        if stripped_gitignore[i : i + needle_len] == stripped_block:
            return True
    return False


def _applies(block: dict[str, object], repo_root: Path) -> bool:
    """Return True if this block must be enforced for the given repo."""
    when: str = block.get("applies_when", "always")  # type: ignore[assignment]
    if when == "always":
        return True
    if when == "pyproject_toml_present":
        return (repo_root / "pyproject.toml").exists()
    # Unknown discriminator — enforce conservatively
    return True


# ---------------------------------------------------------------------------
# Validator entry point
# ---------------------------------------------------------------------------


def validate(repo_root: Path, spec_path: Path | None = None) -> list[str]:
    """Validate the .gitignore in repo_root against the baseline spec.

    Returns a list of human-readable finding strings (empty = clean).
    """
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        return [f"{gitignore_path}: .gitignore not found — all managed blocks missing"]

    gitignore_text = gitignore_path.read_text(encoding="utf-8")

    # File-level suppression
    if _SUPPRESSION_MARKER in gitignore_text:
        return []

    gitignore_lines = gitignore_text.splitlines()

    resolved_spec = spec_path or _locate_spec(repo_root)
    spec = _load_spec(resolved_spec)
    raw_blocks = spec.get("managed_blocks", {})
    if not isinstance(raw_blocks, dict):
        msg = "managed_blocks must be a mapping in gitignore-baseline.yaml"
        raise ValueError(msg)  # error-ok: validator CLI entry point; not a node handler
    managed_blocks: dict[str, object] = raw_blocks

    findings: list[str] = []
    for block_name, block_def in managed_blocks.items():
        if not isinstance(block_def, dict):
            continue
        if not _applies(block_def, repo_root):
            continue
        block_lines = _assemble_block(block_def)
        if not _block_present(gitignore_lines, block_lines):
            start_marker = str(block_def["start_marker"])
            end_marker = str(block_def["end_marker"])
            findings.append(
                f"{gitignore_path}: managed block {block_name!r} is missing or altered "
                f"(expected verbatim block from {start_marker!r} to {end_marker!r})"
            )

    return findings


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the gitignore-baseline validator."""
    parser = argparse.ArgumentParser(
        description="Assert managed .gitignore blocks are present verbatim (OMN-12452).",
    )
    parser.add_argument(
        "repo_root",
        nargs="?",
        type=Path,
        default=Path(),
        help="Path to the repo root to validate (default: current directory).",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=None,
        dest="spec_path",
        help="Explicit path to gitignore-baseline.yaml (default: auto-locate).",
    )
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root.resolve()
    spec_path: Path | None = args.spec_path.resolve() if args.spec_path else None

    try:
        findings = validate(repo_root, spec_path)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"{_VALIDATOR_NAME}: error: {exc}\n")
        return 1

    if not findings:
        return 0

    sys.stderr.write(f"{_VALIDATOR_NAME}: {len(findings)} finding(s):\n")
    for finding in findings:
        sys.stderr.write(f"  {finding}\n")
    sys.stderr.write(
        "\nEnsure each managed block appears verbatim in .gitignore.\n"
        f"Suppress all findings for a file with:  {_SUPPRESSION_MARKER} <reason>\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: CLI entry point requires SystemExit
