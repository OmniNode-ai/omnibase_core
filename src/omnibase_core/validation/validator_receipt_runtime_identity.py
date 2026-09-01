# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime-identity gate for committed receipts (OMN-17308, epic OMN-17306).

The second of two enforcement layers. The first is the type itself:
:class:`~omnibase_core.models.dispatch.model_skill_result.ModelSkillResult`
refuses to CONSTRUCT a receipt at schema >= 1.1.0 without a
``runtime_identity`` block, so no emitting code path can produce one. This
module covers the artifacts -- receipt JSON that has been committed to a repo
as evidence, which may have been written by an older build, hand-edited, or
copied in from elsewhere.

## Rules

* ``MISSING_IDENTITY`` -- at/above the requiring schema version with no block.
* ``INCOMPLETE_IDENTITY`` -- a required distribution is absent from
  ``packages``. Silence about a package is not the same as recording it as
  ABSENT; the first is a gap, the second is a fact.
* ``UNRESOLVED_COMMIT`` -- an entry claims ``source: vcs`` and names no commit.
  Declaring a git origin while being unable to identify the content is the
  OMN-17291 shape: a fresh ``0.38.16`` label over ``omnimarket`` content 11
  commits behind ``origin/dev``.
* ``MALFORMED_RECEIPT`` -- unparseable. Fails closed; an unreadable receipt is
  never treated as an absent one, because "the checker could not read it" was
  itself a pass condition in several of the surfaces this epic replaces.

## Grandfathering

A receipt whose ``schema_version`` is below
:data:`~omnibase_core.models.dispatch.model_skill_result.RUNTIME_IDENTITY_REQUIRED_FROM`
predates the requirement and PASSES. History is never rewritten: back-filling
an identity onto an old receipt would fabricate a claim about a process nobody
observed. Grandfathering is by version rather than by an allowlist so it
expires on its own as old receipts age out, with no file to prune.

CLI::

    python -m omnibase_core.validation.validator_receipt_runtime_identity \\
        --receipts-dir docs/evidence/receipts
    python -m omnibase_core.validation.validator_receipt_runtime_identity a.json b.json

Exit 0 clean, exit 1 on any violation. Wired as a pre-commit hook
(``check-receipt-runtime-identity``) and as the ``receipt-runtime-identity``
CI job in the same PR that introduced it -- an advisory-only check is one
nobody adopts (operating rule 5).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from omnibase_core.enums.enum_package_source_kind import EnumPackageSourceKind
from omnibase_core.enums.enum_runtime_identity_rule import EnumRuntimeIdentityRule
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dispatch.model_skill_result import (
    RUNTIME_IDENTITY_REQUIRED_FROM,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.validation.model_runtime_identity_violation import (
    ModelRuntimeIdentityViolation,
)
from omnibase_core.types.type_json import JsonType

__all__ = [
    "DEFAULT_REQUIRED_PACKAGES",
    "count_receipts",
    "main",
    "scan_receipt_file",
    "scan_receipt_files",
    "scan_receipts_directory",
]

# The distributions a receipt must be able to speak about. These three decide
# whether a receipt describes a local venv or a deployed lane: omnimarket owns
# the node/handler set, omnibase_infra the runtime and CLI, omnibase_core the
# models and dispatch. A stamp silent about any of them cannot settle the
# question the whole epic exists to settle.
DEFAULT_REQUIRED_PACKAGES: tuple[str, ...] = (
    "omnibase_core",
    "omnibase_infra",
    "omnimarket",
)

# Receipts are identified structurally rather than by filename: a receipt is a
# JSON object carrying these keys. Keeps the gate from silently skipping a
# receipt someone named differently -- an unscanned file passing is exactly the
# vacuous-gate shape OMN-14531 catalogued.
_RECEIPT_MARKER_KEYS = frozenset({"skill_name", "node_name", "run_id", "status"})


def _looks_like_receipt(payload: object) -> bool:
    return isinstance(payload, dict) and _RECEIPT_MARKER_KEYS.issubset(payload)


def _parse_schema_version(raw: object) -> ModelSemVer | None:
    """Parse a receipt's ``schema_version``, tolerating both wire shapes.

    Pydantic serialises ``ModelSemVer`` as an object; hand-written fixtures and
    older tooling use the ``"1.0.0"`` string form. Returning ``None`` for
    anything else makes an unparseable version fail closed at the call site
    rather than defaulting to a grandfathered reading.
    """
    if isinstance(raw, str):
        try:
            return ModelSemVer.parse(raw)
        except (ModelOnexError, ValueError, TypeError):
            return None
    if isinstance(raw, dict):
        try:
            return ModelSemVer.model_validate(raw)
        except (ModelOnexError, ValueError, TypeError):
            return None
    return None


def _packages_of(identity: dict[str, JsonType]) -> dict[str, JsonType]:
    packages = identity.get("packages")
    return packages if isinstance(packages, dict) else {}


def _check_identity(
    *,
    path: Path,
    identity: dict[str, JsonType],
    required_packages: Sequence[str],
) -> list[ModelRuntimeIdentityViolation]:
    violations: list[ModelRuntimeIdentityViolation] = []
    packages = _packages_of(identity)

    missing = [name for name in required_packages if name not in packages]
    if missing:
        violations.append(
            ModelRuntimeIdentityViolation(
                path=str(path),
                rule=EnumRuntimeIdentityRule.INCOMPLETE_IDENTITY,
                detail=(
                    "runtime_identity.packages is silent about "
                    f"{', '.join(sorted(missing))}. Record the distribution "
                    "explicitly -- source 'absent' is a fact, omission is a "
                    "gap."
                ),
            )
        )

    for name in sorted(packages):
        entry = packages[name]
        if not isinstance(entry, dict):
            violations.append(
                ModelRuntimeIdentityViolation(
                    path=str(path),
                    rule=EnumRuntimeIdentityRule.MALFORMED_RECEIPT,
                    detail=(f"runtime_identity.packages[{name!r}] is not an object"),
                )
            )
            continue
        if entry.get("source") == EnumPackageSourceKind.SHADOWED.value:
            violations.append(
                ModelRuntimeIdentityViolation(
                    path=str(path),
                    rule=EnumRuntimeIdentityRule.SHADOWED_IMPORT,
                    detail=(
                        f"package {name!r} declares source 'shadowed': install "
                        f"metadata says version={entry.get('version')!r} but "
                        "the interpreter imported the module from "
                        f"{entry.get('import_path')!r}. Every version in this "
                        "receipt names a tree that did not run."
                    ),
                )
            )
            continue
        if entry.get("source") != EnumPackageSourceKind.VCS.value:
            continue
        if not entry.get("commit"):
            violations.append(
                ModelRuntimeIdentityViolation(
                    path=str(path),
                    rule=EnumRuntimeIdentityRule.UNRESOLVED_COMMIT,
                    detail=(
                        f"package {name!r} declares source 'vcs' but names no "
                        f"commit (version={entry.get('version')!r}). A version "
                        "string is a label, not evidence of content."
                    ),
                )
            )
    return violations


def scan_receipt_file(
    path: Path,
    *,
    required_packages: Sequence[str] = DEFAULT_REQUIRED_PACKAGES,
) -> list[ModelRuntimeIdentityViolation]:
    """Scan one JSON file; return every violation it carries.

    A file that is not a receipt at all returns no violations -- the gate is
    scoped to receipts, and a pre-commit hook is handed whatever JSON happens
    to be staged.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            ModelRuntimeIdentityViolation(
                path=str(path),
                rule=EnumRuntimeIdentityRule.MALFORMED_RECEIPT,
                detail=f"could not be read as JSON: {type(exc).__name__}: {exc}",
            )
        ]

    if not _looks_like_receipt(payload):
        return []

    version = _parse_schema_version(payload.get("schema_version"))
    if version is None:
        return [
            ModelRuntimeIdentityViolation(
                path=str(path),
                rule=EnumRuntimeIdentityRule.MALFORMED_RECEIPT,
                detail=(
                    "schema_version is missing or unparseable, so whether "
                    "this receipt is grandfathered cannot be decided. An "
                    "undecidable receipt fails closed."
                ),
            )
        ]

    if version < RUNTIME_IDENTITY_REQUIRED_FROM:
        # Grandfathered: predates the requirement, and saying so is honest.
        return []

    identity = payload.get("runtime_identity")
    if identity is None:
        return [
            ModelRuntimeIdentityViolation(
                path=str(path),
                rule=EnumRuntimeIdentityRule.MISSING_IDENTITY,
                detail=(
                    f"schema_version {version} is at or above "
                    f"{RUNTIME_IDENTITY_REQUIRED_FROM} and carries no "
                    "runtime_identity block, so nothing binds this evidence "
                    "to the process that produced it."
                ),
            )
        ]
    if not isinstance(identity, dict):
        return [
            ModelRuntimeIdentityViolation(
                path=str(path),
                rule=EnumRuntimeIdentityRule.MALFORMED_RECEIPT,
                detail="runtime_identity is present but is not an object",
            )
        ]

    return _check_identity(
        path=path, identity=identity, required_packages=required_packages
    )


def count_receipts(paths: Iterable[Path]) -> int:
    """Return how many of ``paths`` are actually receipts.

    Reported alongside every PASS so a reader can tell a clean scan from a
    vacuous one. OMN-14531 found 16/16 sweeps passing while scanning zero
    items; a gate that cannot say how much it looked at is indistinguishable
    from one that looked at nothing.
    """
    total = 0
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if _looks_like_receipt(payload):
            total += 1
    return total


def scan_receipt_files(
    paths: Iterable[Path],
    *,
    required_packages: Sequence[str] = DEFAULT_REQUIRED_PACKAGES,
) -> list[ModelRuntimeIdentityViolation]:
    """Scan explicit files (the pre-commit ``pass_filenames`` path)."""
    violations: list[ModelRuntimeIdentityViolation] = []
    for path in paths:
        violations.extend(scan_receipt_file(path, required_packages=required_packages))
    return violations


# Directory names never walked by a directory scan. ``.venv`` and
# ``node_modules`` hold vendored JSON by the thousand and no committed
# evidence; walking them would make the gate slow enough to be disabled, which
# is the way a gate actually dies.
_SKIPPED_DIR_NAMES = frozenset({"node_modules", "__pycache__"})


def _is_scannable(path: Path) -> bool:
    return not any(
        part in _SKIPPED_DIR_NAMES or part.startswith(".") for part in path.parent.parts
    )


def scan_receipts_directory(
    root: Path,
    *,
    required_packages: Sequence[str] = DEFAULT_REQUIRED_PACKAGES,
) -> list[ModelRuntimeIdentityViolation]:
    """Scan every committed-looking ``*.json`` under ``root`` (the CI path).

    Hidden directories (``.venv``, ``.git``, ``.mypy_cache``) and vendored
    trees are skipped; nothing committed as evidence lives in them.
    """
    candidates = sorted(p for p in root.rglob("*.json") if _is_scannable(p))
    return scan_receipt_files(candidates, required_packages=required_packages)


def main(argv: list[str] | None = None) -> int:
    """CLI: exit non-zero on any runtime-identity violation.

    Exit codes:
        0 -- clean (including "every receipt found was grandfathered")
        1 -- one or more violations, each printed with rule + detail
    """
    parser = argparse.ArgumentParser(
        description=(
            "Runtime-identity gate (OMN-17308): fail receipts at schema "
            f">= {RUNTIME_IDENTITY_REQUIRED_FROM} that do not identify the "
            "process that produced them."
        )
    )
    parser.add_argument(
        "--receipts-dir",
        default=None,
        help="Directory tree to scan for *.json receipts.",
    )
    parser.add_argument(
        "--require-package",
        action="append",
        default=None,
        metavar="DIST",
        help=(
            "Distribution a stamp must speak about. Repeatable. Default: "
            f"{', '.join(DEFAULT_REQUIRED_PACKAGES)}."
        ),
    )
    parser.add_argument(
        "receipt_paths",
        nargs="*",
        help="Explicit receipt files to scan (pre-commit passes these).",
    )
    args = parser.parse_args(argv)

    required: Sequence[str] = args.require_package or DEFAULT_REQUIRED_PACKAGES

    explicit = [Path(p) for p in args.receipt_paths]
    if explicit:
        candidates = explicit
        target = f"{len(explicit)} explicit file(s)"
    elif args.receipts_dir is not None:
        root = Path(args.receipts_dir)
        if not root.exists():
            print(
                f"ERROR: --receipts-dir does not exist: {root}",
                file=sys.stderr,
            )
            return 1
        candidates = [p for p in sorted(root.rglob("*.json")) if _is_scannable(p)]
        target = str(root)
    else:
        # The only "no target" path, so a mis-wired hook fails loudly instead
        # of scanning nothing and reporting success — a gate that passes
        # because it was handed nothing is the vacuous-PASS failure class this
        # validator exists to close (OMN-14531).
        #
        # Spelled as an explicit usage-print + return rather than argparse's
        # parser.error(): error() terminates only by convention, which left
        # `candidates` and `target` provably-unbound to static analysis (CodeQL
        # py/uninitialized-local-variable, 3 alerts on PR #1634). A validator
        # whose own no-target path can raise UnboundLocalError fails in the
        # least legible way available to it — the operator sees a traceback
        # instead of the refusal the gate meant to give.
        parser.print_usage(sys.stderr)
        print(
            "ERROR: pass receipt files, or --receipts-dir",
            file=sys.stderr,
        )
        return 2

    violations = scan_receipt_files(candidates, required_packages=required)
    receipts = count_receipts(candidates)

    if not violations:
        print(
            f"RUNTIME IDENTITY GATE PASSED: 0 violations across "
            f"{receipts} receipt(s) in {len(candidates)} JSON file(s) "
            f"under {target}"
        )
        return 0

    print(
        f"RUNTIME IDENTITY GATE FAILED: {len(violations)} violation(s) in {target}:\n"
    )
    for violation in violations:
        print(f"  [{violation.rule.value}] {violation.path}")
        print(f"    {violation.detail}")
        print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
