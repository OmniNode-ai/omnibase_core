# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRuntimeShaMatchOutput — payload for runtime_sha_match DoD receipts. OMN-9356"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelRuntimeShaMatchOutput(BaseModel):
    """Structured payload stored in ModelDodReceipt.actual_output for runtime_sha_match checks.

    Serialized as JSON into actual_output. Proves that deployed_sha was
    read from the runtime server and compared against merge_sha.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    runtime_host: str = Field(
        ..., min_length=1, description="IP or hostname of the runtime server probed"
    )
    deployed_sha: str = Field(
        ..., min_length=1, description="Git SHA currently deployed on the runtime"
    )
    merge_sha: str = Field(
        ..., min_length=1, description="Git SHA that was merged to main (PR head)"
    )
    match: bool = Field(..., description="True iff deployed_sha == merge_sha")


__all__ = ["ModelRuntimeShaMatchOutput"]
