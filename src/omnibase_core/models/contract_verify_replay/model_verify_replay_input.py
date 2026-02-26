# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for contract.verify.replay compute node.

.. versionadded:: 0.20.0
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_verify_tier import EnumVerifyTier
from omnibase_core.models.contract_verify_replay.model_verify_options import (
    ModelVerifyOptions,
)

__all__ = ["ModelVerifyReplayInput"]


class ModelVerifyReplayInput(BaseModel):
    """Input for the contract.verify.replay compute node.

    Attributes:
        package_path: Absolute filesystem path to the ``.oncp`` bundle to
            verify. Mutually exclusive with ``package_bytes``.
        package_bytes: Raw in-memory bytes of the ``.oncp`` bundle. Mutually
            exclusive with ``package_path``. Useful for testing without
            touching the filesystem.
        tier: Verification tier to execute. Defaults to
            :attr:`~EnumVerifyTier.TIER1_STATIC`.
        options: Optional runtime options for the verification run.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-path-ok: filesystem path to .oncp bundle, not a UUID
    package_path: str | None = Field(
        default=None,
        description="Absolute path to the .oncp bundle to verify.",
    )
    package_bytes: bytes | None = Field(
        default=None,
        description="In-memory .oncp bundle bytes (for testing).",
    )
    tier: EnumVerifyTier = Field(
        default=EnumVerifyTier.TIER1_STATIC,
        description="Verification tier to execute.",
    )
    options: ModelVerifyOptions = Field(
        default_factory=ModelVerifyOptions,
        description="Runtime options for the verification run.",
    )
