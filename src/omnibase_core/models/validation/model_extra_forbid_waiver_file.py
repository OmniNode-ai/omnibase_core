# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelExtraForbidWaiverFile — expiring-waiver document envelope (OMN-18038).

Typed contract boundary for ``omnibase_core/validators/extra_forbid_waivers.yaml``.

The ENVELOPE is closed and typed here: the document is a mapping carrying exactly a
``waivers`` list. The per-entry field rules (``fqn``/``ticket``/``pr``/``expires_at``
present, well-formed and unexpired) are deliberately NOT enforced by this model —
``pydantic_extra_forbid.load_waivers`` reports each malformed entry as its own named
error so an operator sees every problem in one run. A strict entry model would abort
the whole file on the first bad entry and collapse that error taxonomy into one
opaque ``ValidationError``, which is a worse gate, not a stricter one.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelExtraForbidWaiverFile(BaseModel):
    """Parsed ``extra_forbid_waivers.yaml`` document envelope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    waivers: list[object] = Field(
        default_factory=list,
        description=(
            "Raw waiver entries; each is validated field-by-field by the gate so "
            "that every malformed entry is reported under its own error"
        ),
    )


__all__ = ["ModelExtraForbidWaiverFile"]
