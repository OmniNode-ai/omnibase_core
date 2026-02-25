# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Lockfile entry model — per-command pin record in ``omn.lock``.

Each entry in the lockfile corresponds to one CLI command pinned at a
specific contract fingerprint, publisher, and schema versions.

.. versionadded:: 0.20.0  (OMN-2570)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelLockEntry"]


class ModelLockEntry(BaseModel):
    """A single command entry pinned in the lockfile.

    Each entry captures the exact state of one CLI command at the time
    ``omn lock`` was executed.  CLI invocations with a lockfile present
    verify the current catalog fingerprints against these pinned values.

    Attributes:
        command_id: Globally namespaced, immutable command ID.
            Example: ``com.omninode.memory.query``.
        fingerprint: SHA256 hex fingerprint of the contract at lock time.
            Computed by ``ModelCliContribution.compute_fingerprint()``.
        publisher: Node ID that published this command's contract.
        cli_version_requirement: Minimum CLI version required to invoke
            this command.  Empty string means no version requirement.
        args_schema_ref: Registry reference to the argument schema pinned
            at lock time.
        output_schema_ref: Registry reference to the output schema pinned
            at lock time.
    """

    # string-id-ok: dot-notation namespaced CLI command ID (e.g. com.omninode.memory.query), not a UUID
    command_id: str = Field(
        ...,
        min_length=5,
        description="Globally namespaced, immutable command ID (dot notation).",
    )
    fingerprint: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
        description="SHA256 hex fingerprint of the contract commands payload.",
    )
    publisher: str = Field(
        ...,
        min_length=1,
        description="Node ID of the publisher that owns this command.",
    )
    # string-version-ok: free-form SemVer constraint string (e.g. ">=0.20.0"), not a pinned ModelSemVer
    cli_version_requirement: str = Field(
        default="",
        description=(
            "Minimum CLI version required (SemVer string). "
            "Empty string means no version requirement."
        ),
    )
    args_schema_ref: str = Field(
        ...,
        min_length=1,
        description="Registry reference to the argument schema at lock time.",
    )
    output_schema_ref: str = Field(
        ...,
        min_length=1,
        description="Registry reference to the output schema at lock time.",
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )
