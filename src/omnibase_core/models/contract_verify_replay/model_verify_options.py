# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Options model for contract.verify.replay.

.. versionadded:: 0.20.0
"""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelVerifyOptions"]


class ModelVerifyOptions(BaseModel):
    """Runtime options for a verify-replay run.

    MVP: all options are optional and default to sensible values. Extended
    options (signing key path, sandbox config) are deferred to future tickets.

    Attributes:
        skip_digest_check: When True, skip content-hash verification of bundle
            entries (useful for ad-hoc debugging). Defaults to False.
        strict_overlay_ordering: When True, raise if overlay scopes are
            out of canonical order instead of auto-sorting. Defaults to False.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    skip_digest_check: bool = False
    strict_overlay_ordering: bool = False
