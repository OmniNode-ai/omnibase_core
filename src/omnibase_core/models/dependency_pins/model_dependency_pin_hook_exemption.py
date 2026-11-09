# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One hook revision exempt from the release-count bound until a date (OMN-23246)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDependencyPinHookExemption"]


class ModelDependencyPinHookExemption(BaseModel):
    """A single pinned hook revision allowed past ``hook_rev_max_releases_behind``.

    The exemption names one revision of one hook repository, so it exempts nothing
    else: the next rev, another hook repository and every other consumer pin are
    judged by the bound as before. It always expires. Past ``expires`` the check
    fails on the pin, whether or not the pin is still behind the bound, so the
    entry is removed or the pin moved.

    Attributes:
        url: The ``repo:`` URL of the hook repository, as in ``hook_repos``.
        rev: The first 12 characters of the one commit sha the pre-commit config pins. The
            pin itself must be a full 40-character sha, so the entry names a single immutable
            commit; a tag, branch or short ref is never exempt.
        expires: The last day (UTC) the exemption applies; the check fails after it.
        ruling: The operator ruling that allows this entry, starting ``RULING <UTC stamp>``.
        ticket: The ticket that moves the pin inside the bound and removes the entry.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    url: str = Field(min_length=1)
    rev: str = Field(pattern=r"^[0-9a-f]{12}$")
    expires: date
    ruling: str = Field(
        pattern=r"^RULING [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\b.*"
    )
    ticket: str = Field(pattern=r"^OMN-[0-9]+$")
