# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed capture of a ``[skip-<gate>: <reason>]`` bypass token (OMN-14187).

Piece 1/5 of the canonical OCC stamp-model (parent epic OMN-14180). This model
is the single typed vocabulary for the skip-token detection that lives in two
places today:

* ``omniclaude/.pre-commit-hooks/reject-deploy-gate-skip-token.sh`` —
  ``SKIP_PATTERN='\\[skip-[a-zA-Z]'`` and
  ``ALLOWLIST_PATTERN='#\\s*skip-token-allowed:\\s*\\S'``.
* ``omnibase_core.validation.validator_receipt_gate`` — ``SKIP_TOKEN_PATTERN``
  (``\\[skip-[a-zA-Z][^\\]<>]*\\]``) and ``ALLOWLIST_PATTERN``
  (``#\\s*skip-token-allowed:\\s*(\\S+)``).

The allowlist receipt id is captured from the separate, out-of-band
``# skip-token-allowed: <id>`` companion line — it is NOT nested inside the
bracket token. Pure Pydantic domain model: zero I/O.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field


class ModelPrReceiptGateSkipToken(BaseModel):
    """A ``[skip-<gate_name>: <reason>]`` bypass token and its allowlist state.

    ``gate_name`` is the identifier after ``skip-`` (e.g. ``receipt-gate``,
    ``deploy-gate``); its pattern mirrors the leading-alpha requirement of the
    hook's ``SKIP_PATTERN`` while pinning the full safe-identifier shape.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    gate_name: str = Field(min_length=1, pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$")
    reason: str = Field(default="")
    allowlist_receipt_id: str | None = Field(default=None)

    @property
    def is_allowlisted(self) -> bool:
        """True when an out-of-band ``# skip-token-allowed: <id>`` id is bound."""
        return self.allowlist_receipt_id is not None

    def render_token(self) -> str:
        """Return the bracket token as it appears in a PR body / commit message."""
        return f"[skip-{self.gate_name}: {self.reason}]"

    def as_dict(self) -> dict[str, object]:
        return {
            "gate_name": self.gate_name,
            "reason": self.reason,
            "allowlist_receipt_id": self.allowlist_receipt_id,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


__all__ = ["ModelPrReceiptGateSkipToken"]
