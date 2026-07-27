# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Content-anchor validation for dispatch report models (OMN-15161).

Fleet-generic port of steel_onslaught PR #213's ``check_content_anchors`` /
``_sha_resolves`` (originally ``scripts/check_report_contract.py``), as
IMPORTABLE LIBRARY CODE -- deliberately not a CLI script. The consuming
COMPUTE node (``node_report_validation_compute``) is a separate omnimarket
ticket (OMN-15163); this module supplies the git-SHA-resolution and
path-containment checks that node calls, so the two do not diverge.

2026-07-25 finding: seven dispatched agents returned bare acknowledgements
in place of a typed final result, and one filled a required 4-field schema
with the literal string ``"test"`` in every field -- which VALIDATED,
because the schema in use checked shape only. The typed pydantic contracts
in ``omnibase_core.models.dispatch.report`` close the self-contained checks
(verdict is a closed enum, ``pr_number`` is a positive int, free text is
rejected on placeholder/bare-ack patterns and on under-length filler); this
module supplies the second pass for the checks that need live repo state --
a git SHA field must resolve to a real commit, and artifact-path fields must
resolve, *and stay contained*, under a caller-supplied repo root, to files
that actually exist. An artifact path that escapes the repo root
(``../../../etc/hosts``, or an absolute path such as ``/etc/hosts``) is
rejected even if it resolves to a real file on disk.

Field-name-suffix convention (mirrors
``omnibase_core.models.dispatch.report``): any field ending ``_sha`` is
checked via ``git cat-file -e`` in the caller-supplied ``git_dir``; any field
ending ``_paths`` (a list of strings) is resolved under the caller-supplied
``repo_root`` and checked both for containment (the resolved path must stay
under ``repo_root``) and for existence. This is generic over all four
current roles and any future role added to ``ROLE_TO_MODEL`` without
touching this module.

Fail-closed semantics: a content-anchor-bearing field present on the report
with its checking context (``git_dir``/``repo_root``) withheld is a
VIOLATION, never a silent pass -- "optional input means the check does not
exist" (``feedback_optional_input_means_the_check_does_not_exist``).

Note on git subprocess safety: ``_sha_resolves`` invokes
``git --git-dir <path> cat-file -e <sha>`` with an EXPLICIT ``--git-dir``
flag rather than ``-C``/``cwd``. Git's own argument precedence makes an
explicit ``--git-dir`` flag win over an inherited ``GIT_DIR`` environment
variable (verified empirically; the OMN-14891 corruption class the
``no_unguarded_git_subprocess`` gate guards against is specifically the
``-C``/``cwd``-only pattern, which env ``GIT_DIR`` silently overrides), so no
additional environment scrub is required here.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = ["check_dispatch_report_content_anchors"]


def _sha_resolves(git_dir: Path, sha: str) -> bool:
    # `^{commit}` peels the object reference and requires it to dereference to
    # a COMMIT specifically -- plain `cat-file -e <sha>` (no peel) succeeds for
    # any object type (blob, tree, tag), so a blob hash would otherwise satisfy
    # a `head_sha`/`verified_sha`/`merge_sha` content anchor despite the
    # contract requiring a real commit.
    result = subprocess.run(
        ["git", "--git-dir", str(git_dir), "cat-file", "-e", f"{sha}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def check_dispatch_report_content_anchors(
    report: BaseModel, *, git_dir: Path | None, repo_root: Path | None
) -> list[str]:
    """Return SPECIFIC violation strings for every content-anchor field on
    ``report`` that fails to resolve (or whose required context was not
    provided). ``[]`` means every anchor on this report checked out.

    Args:
        report: A validated dispatch report model instance (one of
            ``omnibase_core.models.dispatch.report.ROLE_TO_MODEL``'s values).
        git_dir: The git dir (e.g. ``<worktree>/.git``) used to resolve any
            ``*_sha`` content anchor field. ``None`` fails closed for any
            report carrying a non-``None`` ``*_sha`` field.
        repo_root: The repo root used to resolve any ``*_paths`` artifact
            content anchor field. ``None`` fails closed for any report
            carrying a non-empty ``*_paths`` field.
    """
    violations: list[str] = []
    for field_name in type(report).model_fields:
        value = getattr(report, field_name)
        if field_name.endswith("_sha"):
            if value is None:
                continue
            if git_dir is None:
                violations.append(
                    f"field '{field_name}' is a git-SHA content anchor ({value!r}) but "
                    "git_dir was not provided -- an unchecked anchor is a fail-closed violation"
                )
                continue
            if not git_dir.exists():
                violations.append(f"git_dir does not exist: {git_dir}")
                continue
            if not _sha_resolves(git_dir, str(value)):
                violations.append(
                    f"field '{field_name}' SHA {value!r} does not resolve to a real commit "
                    f"in git_dir {git_dir}"
                )
        elif field_name.endswith("_paths"):
            if not value:
                continue
            if repo_root is None:
                violations.append(
                    f"field '{field_name}' is an artifact-path content anchor ({value!r}) but "
                    "repo_root was not provided -- an unchecked anchor is a fail-closed violation"
                )
                continue
            resolved_root = repo_root.resolve()
            for artifact in value:
                # Resolve BEFORE checking existence, and require the resolved
                # path to stay under resolved_root. Existence alone is not
                # containment: pathlib silently discards repo_root entirely
                # when `artifact` is itself absolute (`repo_root / "/etc/hosts"
                # == Path("/etc/hosts")`), and `../../../etc/hosts` walks out
                # via `..` segments -- both resolve to a real file outside the
                # repo and must never pass. `.resolve()` also follows
                # symlinks, so a committed symlink pointing outside the repo
                # is caught the same way.
                resolved_artifact = (repo_root / artifact).resolve()
                try:
                    resolved_artifact.relative_to(resolved_root)
                except ValueError:
                    violations.append(
                        f"field '{field_name}' cites an artifact path that escapes "
                        f"repo_root {repo_root} (resolves to {resolved_artifact}): {artifact}"
                    )
                    continue
                if not resolved_artifact.exists():
                    violations.append(
                        f"field '{field_name}' cites an artifact path that does not exist under "
                        f"repo_root {repo_root}: {artifact}"
                    )
                elif not resolved_artifact.is_file():
                    # Catches a directory citation generally -- including the
                    # degenerate case of the artifact resolving to repo_root
                    # itself (e.g. "", ".", or an equivalent traversal): a
                    # directory satisfies containment and existence without
                    # anchoring any actual artifact, which is not what a
                    # "*_paths" content anchor means.
                    violations.append(
                        f"field '{field_name}' cites an artifact path that is not a file "
                        f"under repo_root {repo_root}: {artifact}"
                    )
    return violations
