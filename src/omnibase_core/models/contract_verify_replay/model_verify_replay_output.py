# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Output model (signed verification report) for contract.verify.replay.

The report is the primary artifact produced by
:class:`~omnibase_core.nodes.node_contract_verify_replay_compute.handler.NodeContractVerifyReplayCompute`.
It captures the tier checked, per-check outcomes, overall pass/fail status,
content hash of the verified package, and an ed25519 signature of the report.

.. versionadded:: 0.20.0
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_verify_tier import EnumVerifyTier
from omnibase_core.models.contract_verify_replay.model_verify_check_result import (
    ModelVerifyCheckResult,
)

__all__ = ["ModelVerifyReplayOutput"]

OverallStatus = Literal["pass", "fail", "error"]


class ModelVerifyReplayOutput(BaseModel):
    """Signed verification report produced by contract.verify.replay.

    The ``report_digest`` field is the canonical SHA-256 of the report content
    (excluding ``report_digest`` and ``signature`` themselves). The ``signature``
    field holds the base64-encoded ed25519 signature over that digest, produced
    with the local verifier key at ``~/.onex/verifier.key``.

    Attributes:
        report_version: Schema version of the report format. Currently ``1``.
        tier: The verification tier that was executed.
        package_content_hash: ``sha256:<hex>`` digest of the raw ``.oncp``
            bundle bytes that were verified.
        package_id: Package identifier from the bundle manifest.
        package_version: Package version from the bundle manifest.
        checks: Ordered list of per-check results.
        overall_status: Aggregated outcome. ``"pass"`` iff all required checks
            passed; ``"fail"`` if any check failed; ``"error"`` if the
            verification run itself raised an unexpected exception.
        generated_at: UTC timestamp when the report was produced.
        report_digest: ``sha256:<hex>`` digest of the serialised report content
            (excluding this field and ``signature``). Used to verify the
            signature without re-hashing.
        signature: Base64-encoded ed25519 signature of ``report_digest``.
            ``None`` when no verifier key is available (key-less mode).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    report_version: int = Field(
        default=1,
        ge=1,
        description="Schema version of the report format.",
    )
    tier: EnumVerifyTier = Field(..., description="Verification tier executed.")
    # string-id-ok: package IDs are reverse-dotted names, not UUIDs
    package_id: str = Field(..., min_length=1, description="Package identifier.")
    # string-version-ok: SemVer string from the bundle manifest
    package_version: str = Field(..., min_length=1, description="Package version.")
    package_content_hash: str = Field(
        ...,
        min_length=1,
        description="sha256:<hex> digest of the raw .oncp bundle bytes.",
    )
    checks: list[ModelVerifyCheckResult] = Field(
        default_factory=list,
        description="Per-check results in execution order.",
    )
    overall_status: OverallStatus = Field(
        ...,
        description="Aggregated outcome: pass, fail, or error.",
    )
    generated_at: datetime = Field(
        ...,
        description="UTC timestamp when the report was produced.",
    )
    report_digest: str = Field(
        ...,
        min_length=1,
        description="sha256:<hex> digest of the report content (excl. signature).",
    )
    signature: str | None = Field(
        default=None,
        description=(
            "Base64-encoded ed25519 signature over report_digest. "
            "None when no verifier key is available."
        ),
    )
