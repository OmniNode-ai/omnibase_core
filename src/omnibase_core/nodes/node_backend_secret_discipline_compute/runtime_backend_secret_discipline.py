# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Command line runtime of the backend secret discipline node (OMN-13305).

Reads the supplied config files (or the files a git diff names), hands their
contents to the pure ``build_report_from_files`` and prints the verdict. The
pre-commit hook and CI call::

    python -m omnibase_core.nodes.node_backend_secret_discipline_compute.runtime_backend_secret_discipline
    python -m ...runtime_backend_secret_discipline --json
    python -m ...runtime_backend_secret_discipline file1.yaml file2.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.git_file_listing.model_git_file_listing_input import (
    ModelGitFileListingInput,
)
from omnibase_core.models.validation.model_backend_secret_discipline_output import (
    ModelBackendSecretDisciplineOutput,
)
from omnibase_core.nodes.node_git_file_listing_effect.handler import (
    NodeGitFileListingEffect,
)
from omnibase_core.validation.validator_backend_secret_discipline import (
    build_report_from_files,
)

_REPO_ROOT_MARKER = ".git"
_CONFIG_SUFFIXES: frozenset[str] = frozenset({".yaml", ".yml", ".json"})


def _find_repo_root(start: Path) -> Path:
    candidate = start
    while candidate != candidate.parent:
        if (candidate / _REPO_ROOT_MARKER).exists():
            return candidate
        candidate = candidate.parent
    return start


def _run_on_files(paths: list[Path]) -> ModelBackendSecretDisciplineOutput:
    """Run the check on the explicitly supplied file paths."""
    repo_root = _find_repo_root(paths[0] if paths else Path.cwd())
    contents: dict[str, str] = {}
    for path in paths:
        try:
            rel = str(path.relative_to(repo_root))
        except ValueError:
            rel = str(path)
        contents[rel] = path.read_text(encoding="utf-8")
    return build_report_from_files(contents)


def _say(text: str) -> None:
    sys.stdout.write(f"{text}\n")


def _git_changed_files(base: str) -> list[Path] | None:
    """The files ``base...HEAD`` changes, or ``None`` after naming the git error."""
    try:
        listing = NodeGitFileListingEffect().handle(
            ModelGitFileListingInput(root=Path.cwd(), scope="diff", base_ref=base)
        )
    except ModelOnexError as exc:
        sys.stderr.write(f"{exc.message}\n")
        return None
    if listing.fell_back_to_all:
        sys.stderr.write(f"cannot diff HEAD against {base!r}\n")
        return None
    return [Path(p) for p in listing.paths]


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry-point for pre-commit hook and standalone invocation.

    Returns:
        0 on PASS, 1 on FAIL.
    """
    parser = argparse.ArgumentParser(
        description="Backend secret-ref / credential-ref discipline gate (OMN-13305)"
    )
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    parser.add_argument(
        "--base",
        default=None,
        help="Git base ref to diff HEAD against (CI mode); scans changed config files.",
    )
    parser.add_argument(
        "filenames",
        nargs="*",
        help="Files to check (pre-commit passes staged filenames here)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.base is not None:
        changed = _git_changed_files(args.base)
        if changed is None:
            return 2
        paths = changed
    else:
        paths = [Path(f) for f in args.filenames]

    config_paths = [p for p in paths if p.suffix in _CONFIG_SUFFIXES]
    if not config_paths:
        if args.json:
            _say(
                json.dumps(
                    {
                        "gate": "backend-secret-discipline",
                        "passed": True,
                        "note": "no config files to check",
                    },
                    indent=2,
                )
            )
        else:
            _say("[backend-secret-discipline] PASS - no config files to check.")
        return 0

    report = _run_on_files(config_paths)

    if args.json:
        # Convert Pydantic models to dicts for JSON output.
        _say(
            json.dumps(
                {
                    "ticket": report.ticket,
                    "gate": report.gate,
                    "literal_credential_violations": [
                        v.model_dump() for v in report.literal_credential_violations
                    ],
                    "backend_ref_violations": [
                        v.model_dump() for v in report.backend_ref_violations
                    ],
                    "errors": report.errors,
                    "passed": report.passed,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if report.passed else 1

    if report.passed:
        _say(
            "[backend-secret-discipline] PASS — no literal credentials; every "
            "authenticated cloud backend declares a logical secret/credential ref."
        )
        return 0

    _say("[backend-secret-discipline] FAIL")
    for err in report.errors:
        _say(f"  error: {err}")
    for cred_v in report.literal_credential_violations:
        _say(f"  literal-credential: {cred_v.message}")
    for ref_v in report.backend_ref_violations:
        _say(f"  backend-ref: {ref_v.message}")
    _say(
        "\nFix: keep credential VALUES in the secret store; declare only logical "
        "refs (secret_ref / credential_ref) in routing-authority config."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
