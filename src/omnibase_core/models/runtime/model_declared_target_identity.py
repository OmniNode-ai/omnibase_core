# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A target's own declaration of what it is (OMN-17312).

The other half of the probe-target assertion. A probe that names a target
("this proves the ``.201`` dev lane") is asserting a relationship between the
process that ran and a place; this model is the *place's* statement about
itself, against which that assertion is checked.

## Declared, not intended

Every field here must come from a surface the target emits about itself — the
deployed ``build-provenance.json``, an installed ``direct_url.json`` read back
out of the running container, a lane manifest. ``declared_by`` records which
surface, and is required.

A caller-supplied "I meant the dev lane" is not a declaration; it is the intent
that was already wrong in OMN-17295, where the operator correctly prepared the
lane, correctly believed the probe addressed it, and was correctly told the
probe succeeded — while the orchestrator ran on the laptop.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_execution_locus_kind import EnumExecutionLocusKind

__all__ = ["ModelDeclaredTargetIdentity"]

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class ModelDeclaredTargetIdentity(BaseModel):
    """What a probe target declares itself to be."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    target_name: str = Field(
        ...,
        min_length=1,
        description="Human-readable name of the target, for the failure "
        "message only. Never compared.",
    )
    declared_by: str = Field(
        ...,
        min_length=1,
        description=(
            "The surface this declaration was read from (e.g. the deployed "
            "build-provenance.json path, or a container-id readback command). "
            "Required: a declaration with no provenance is the caller's "
            "intent wearing a declaration's shape."
        ),
    )
    host: str | None = Field(
        default=None,
        description="Hostname the target runs on, when declared.",
    )
    locus_kind: EnumExecutionLocusKind | None = Field(
        default=None,
        description="Whether the target is a container, a venv, or a system "
        "interpreter, when declared.",
    )
    execution_locus: str | None = Field(
        default=None,
        description="The target's container id or venv prefix, when declared.",
    )
    packages: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Expected full 40-character commit per distribution name. This is "
            "the field that catches OMN-17291: a lane whose declared "
            "omnimarket commit is origin/dev's tip, asserted against a stamp "
            "naming an 11-commits-behind SHA."
        ),
    )

    @field_validator("packages")
    @classmethod
    def _validate_commits(cls, value: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for name, commit in value.items():
            candidate = commit.strip().lower()
            if not _COMMIT_RE.match(candidate):
                msg = (
                    f"declared commit for {name!r} must be a full "
                    "40-character lowercase hex git SHA (an abbreviation "
                    f"cannot be compared for identity), got: {commit!r}"
                )
                raise ValueError(msg)
            normalized[name] = candidate
        return normalized

    def is_empty(self) -> bool:
        """True when this declaration asserts nothing comparable.

        ``target_name`` and ``declared_by`` are metadata, not claims, so a
        declaration carrying only those two compares zero fields. The
        assertion helper refuses such a declaration rather than returning a
        pass that proves nothing (OMN-14531's vacuous-check class).
        """
        return (
            self.host is None
            and self.locus_kind is None
            and self.execution_locus is None
            and not self.packages
        )
