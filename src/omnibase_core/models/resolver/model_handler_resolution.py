# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelHandlerResolution - return value from HandlerResolver.resolve().

Frozen Pydantic model encoding the terminal decision of the resolver's
precedence chain for one handler. See
`docs/plans/2026-04-18-handler-resolver-architecture.md` §"Skip Semantics".

Return contract:
    - On successful construction via any precedence path (node registry,
      container, event-bus injection, zero-arg), `outcome` is the matching
      `EnumHandlerResolutionOutcome` value and `handler_instance` is the
      constructed handler instance.
    - On deliberate ownership skip, `outcome` is
      `RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP`, `handler_instance` is None,
      `skipped_handler` carries the handler-name identifier, and
      `skipped_reason` carries the human-readable reason text.
    - `UNRESOLVABLE` is NOT returned — the resolver raises `TypeError`
      when the precedence chain is exhausted (OMN-8735 fail-fast
      invariant). See §"Skip Semantics" for the skip-vs-failure contract.

Justification for introducing this model rather than reusing existing
core/spi types: no comparable decision-result model exists in either repo.
`EnumHandlerResolutionOutcome` alone cannot carry the instance or the skip
metadata.

Layering (permanent, see §"Layering Invariants" in the plan):
    `handler_instance` is typed `object | None`. Narrowing is blocked by
    the compat -> core -> spi -> infra layering rule; the concrete handler
    protocol lives in `omnibase_spi` (`ProtocolHandleable`) and cannot be
    referenced from `omnibase_core`. If a core-safe narrowing becomes
    available in a future phase, tighten here first.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_handler_resolution_outcome import (
    EnumHandlerResolutionOutcome,
)


class ModelHandlerResolution(BaseModel):
    """Terminal decision record returned by `HandlerResolver.resolve()`."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

    outcome: EnumHandlerResolutionOutcome = Field(
        ...,
        description="Which precedence branch resolved this handler (or skip).",
    )
    handler_instance: object | None = Field(
        default=None,
        description=(
            "Constructed handler instance. None iff outcome is "
            "RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP. Typed object | None "
            "per layering invariants."
        ),
    )
    # Preserve the handler name on SKIP so wiring reports can cite which
    # handler was skipped without re-deriving from context.
    skipped_handler: str = Field(
        default="",
        description=(
            "Handler-name identifier preserved on SKIP. Empty string on "
            "successful resolution."
        ),
    )
    skipped_reason: str = Field(
        default="",
        description=(
            "Human-readable reason text for a SKIP outcome. Empty string "
            "on successful resolution."
        ),
    )

    @model_validator(mode="after")
    def _enforce_outcome_invariants(self) -> Self:
        """Enforce outcome-dependent invariants per module docstring contract.

        SKIP outcome:
            - handler_instance MUST be None
            - skipped_handler and skipped_reason MUST be non-empty

        All other outcomes:
            - handler_instance MUST NOT be None
            - skipped_handler and skipped_reason MUST be empty strings

        Comparison uses `==` (value equality), not `is` (identity), per the
        Pydantic/enum convention. See OMN-9196.
        """
        is_skip = (
            self.outcome
            == EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP
        )
        if is_skip:
            if self.handler_instance is not None:
                raise ValueError(
                    "SKIP outcome requires handler_instance=None; "
                    f"got {type(self.handler_instance).__name__}"
                )
            if not self.skipped_handler:
                raise ValueError("SKIP outcome requires non-empty skipped_handler")
            if not self.skipped_reason:
                raise ValueError("SKIP outcome requires non-empty skipped_reason")
        else:
            if self.handler_instance is None:
                raise ValueError(
                    f"Non-skip outcome {self.outcome.name} requires "
                    "handler_instance to be non-None"
                )
            if self.skipped_handler:
                raise ValueError(
                    f"Non-skip outcome {self.outcome.name} requires "
                    "skipped_handler to be empty"
                )
            if self.skipped_reason:
                raise ValueError(
                    f"Non-skip outcome {self.outcome.name} requires "
                    "skipped_reason to be empty"
                )
        return self


__all__ = ["ModelHandlerResolution"]
