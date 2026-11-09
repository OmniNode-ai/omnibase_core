# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One pinned hook revision whose release-count bound differs from the default.

A hook block is sometimes held at an older revision on purpose, because the
newer revision's rule cannot be adopted until separate work lands. The default
``hook_rev_max_releases_behind`` then fires on a clock rather than on a defect:
the consumer's pull requests go red on the day the hook repository cuts its
Nth release, with nothing in the consumer changed.

An override is the declared form of that hold. It is keyed on the held
revision's **conventional abbreviation**, so it retires itself the moment the
block moves, and it carries the ticket that removes the hold and the reason the
newer revision cannot be taken, so a reader can tell a priced exception from a
forgotten pin.

The key is an abbreviation rather than the full sha because a 40-character hex
literal reads as a high-entropy secret: it would oblige this contract to grow
either a secrets-baseline entry or a suppression comment, and the
canonical-file-shape ratchet (OMN-20304) refuses both. An abbreviation of at
least 12 characters is how git itself names a commit in prose, and it is matched
as a prefix of the pinned revision, so it identifies exactly one block.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelDependencyPinHookRevOverride"]

_REV_PREFIX = re.compile(r"\A[0-9a-f]{12,39}\Z")
_TICKET = re.compile(r"\A[A-Z][A-Z0-9]*-[0-9]+\Z")


class ModelDependencyPinHookRevOverride(BaseModel):
    """A pinned hook revision, its own release-count bound and why it is held.

    Attributes:
        rev_prefix: The held revision's abbreviation, 12 to 39 lowercase hex
            characters, matched as a prefix of the pinned revision. A tag is never
            an override subject: the bound exists to move a block onto the newest
            tag, and a sha is what a deliberate hold looks like. When the block's
            rev changes, the prefix stops matching and the default bound applies
            again. Twelve is the floor because a shorter prefix can name more than
            one commit; the full 40 is refused because it reads as a secret.
        max_releases_behind: The bound for this revision. It is ``ge`` the default
            or the override buys nothing; the policy's validator refuses a value
            below the default rather than silently tightening one block.
        ticket: The ticket that removes the hold, so the override has an owner.
        justification: Why the newer revision cannot be adopted yet. Required, and
            at least one sentence: an override with no stated reason is a forgotten
            pin with a longer leash.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rev_prefix: str = Field(min_length=12, max_length=39)
    max_releases_behind: int = Field(ge=0)
    ticket: str = Field(min_length=3)
    justification: str = Field(min_length=20)

    @field_validator("rev_prefix")
    @classmethod
    def _is_rev_prefix(cls, value: str) -> str:
        if not _REV_PREFIX.fullmatch(value):
            raise ValueError(
                "rev_prefix must be 12 to 39 lowercase hex characters of the held "
                "commit sha, never a tag and never the full 40"
            )
        return value

    @field_validator("ticket")
    @classmethod
    def _is_ticket(cls, value: str) -> str:
        if not _TICKET.fullmatch(value):
            raise ValueError("ticket must be an issue identifier such as OMN-22360")
        return value
