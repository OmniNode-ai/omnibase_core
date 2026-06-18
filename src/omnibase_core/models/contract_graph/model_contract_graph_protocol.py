# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ContractGraphProtocol — a protocol/interface reference node typing.

Phase 2 Contract Graph IR (OMN-13132, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2).

Purpose: a Contract Graph IR node may type its boundary against a protocol /
interface (the SPI protocols a node implements, or the renderer protocol a UI
component requires). ``ModelContractGraphProtocol`` is the minimal typed
reference to such a protocol so the IR can carry ``IMPLEMENTS_PROTOCOL`` edges
without inlining the protocol's full definition. It names the protocol and the
input/output model symbols it constrains — nothing more — keeping the IR an
intermediate, not a re-derivation of the protocol source.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelContractGraphProtocol"]


class ModelContractGraphProtocol(BaseModel):
    """A minimal typed reference to a protocol/interface in the IR.

    Records the protocol's qualified name and the input/output model symbols it
    constrains (when the source contract declares them). This is a *reference*,
    not the protocol body: the IR keeps protocols as typed boundary markers so
    ``IMPLEMENTS_PROTOCOL`` edges are well-typed without inlining SPI source.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    protocol_id: str = Field(  # string-id-ok: semantic protocol label, not a UUID
        ...,
        description="Stable semantic identifier for this protocol reference",
        min_length=1,
    )
    qualified_name: str = Field(
        ...,
        description="Fully-qualified protocol/interface name (e.g. dotted import path)",
        min_length=1,
    )
    input_model: str | None = Field(
        default=None,
        description="Qualified input-model symbol the protocol boundary accepts, if declared",
    )
    output_model: str | None = Field(
        default=None,
        description="Qualified output-model symbol the protocol boundary produces, if declared",
    )
