# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic OmniGate diff and config hashing helpers."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

DETERMINISTIC_DIFF_FLAGS: tuple[str, ...] = (
    "--binary",
    "--full-index",
    "--no-renames",
)


def _sha256_prefixed(content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    return f"sha256:{digest}"


def _build_diff_args(base_ref: str | None, head_ref: str | None) -> list[str]:
    if (base_ref is None) != (head_ref is None):
        raise ModelOnexError(
            "base_ref and head_ref must be provided together",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    if base_ref is not None and head_ref is not None:
        return [
            "git",
            "diff",
            *DETERMINISTIC_DIFF_FLAGS,
            f"{base_ref}...{head_ref}",
        ]

    return ["git", "diff", "--staged", *DETERMINISTIC_DIFF_FLAGS]


def compute_diff_hash(
    repo_path: Path,
    *,
    base_ref: str | None = None,
    head_ref: str | None = None,
    allow_empty: bool = False,
) -> str:
    """Compute a SHA256 hash for a staged or explicit base/head git diff."""
    args = _build_diff_args(base_ref, head_ref)
    result = subprocess.run(
        args,
        cwd=repo_path,
        capture_output=True,
        check=True,
    )
    diff_content = result.stdout
    if diff_content or allow_empty:
        return _sha256_prefixed(diff_content)

    if base_ref is not None and head_ref is not None:
        raise ModelOnexError(
            "No PR diff found for the provided base_ref and head_ref. "
            "OmniGate receipts must bind to a non-empty PR diff unless "
            "allow_empty is explicitly enabled for development or tests.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    raise ModelOnexError(
        "No staged diff found. Stage changes with `git add` before running "
        "OmniGate, or pass allow_empty=True for empty-diff receipts.",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    )


def compute_staged_diff_hash(repo_path: Path, *, allow_empty: bool = False) -> str:
    """Compute the deterministic hash for the local staged diff."""
    return compute_diff_hash(repo_path, allow_empty=allow_empty)


def compute_pr_diff_hash(
    repo_path: Path,
    *,
    base_sha: str,
    head_sha: str,
    allow_empty: bool = False,
) -> str:
    """Compute the deterministic hash for a trusted PR base/head diff."""
    return compute_diff_hash(
        repo_path,
        base_ref=base_sha,
        head_ref=head_sha,
        allow_empty=allow_empty,
    )


def compute_config_hash(config_path: Path) -> str:
    """Compute a SHA256 hash from raw config file bytes."""
    return _sha256_prefixed(config_path.read_bytes())
