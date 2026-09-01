# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime-identity gate rule enum (OMN-17308).

The closed set of ways a receipt can fail the runtime-identity gate
(``omnibase_core.validation.validator_receipt_runtime_identity``). Kept in
``enums/`` rather than beside the validator so the validator module holds no
classes and needs no one-class-per-file allowlist entry.
"""

from enum import StrEnum, unique


@unique
class EnumRuntimeIdentityRule(StrEnum):
    """Why a receipt failed the runtime-identity gate."""

    MISSING_IDENTITY = "missing_identity"
    """The receipt is at or above the requiring schema version and carries no
    ``runtime_identity`` block at all."""

    INCOMPLETE_IDENTITY = "incomplete_identity"
    """A required package is absent from ``runtime_identity.packages``. A stamp
    that omits a package is silent about it, which is the state this gate
    exists to make impossible."""

    UNRESOLVED_COMMIT = "unresolved_commit"
    """A package declares ``source: vcs`` but names no commit. Claiming a git
    origin while being unable to identify the content is the OMN-17291 shape —
    a fresh label over stale content."""

    SHADOWED_IMPORT = "shadowed_import"
    """A package declares ``source: shadowed`` — its install metadata describes
    one tree while the interpreter imported another. The receipt's own stamp
    says the code that ran is not the code the versions name, so the receipt
    cannot be read as evidence about the named build."""

    MALFORMED_RECEIPT = "malformed_receipt"
    """The file could not be parsed as a receipt at all. Fails closed: an
    unreadable receipt is never treated as an absent one."""


__all__: list[str] = ["EnumRuntimeIdentityRule"]
