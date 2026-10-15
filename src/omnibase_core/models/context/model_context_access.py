# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextAccess — who a context-source read is for (OMN-18531 / TC.1).

Set by the pack orchestrator from the command envelope, never from the
payload. A request without a tenant is refused at construction, so a source
cannot answer a read whose tenant is unknown.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

__all__ = ["ModelContextAccess"]

# The envelope's tenant is a named slug (for example "lab"), not a UUID, and a
# principal is a name on the bus; both are non-blank text.
_NonBlankName = Annotated[str, StringConstraints(min_length=1)]


class ModelContextAccess(BaseModel):
    """Tenant and principal a context-source read is made on behalf of."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    tenant_id: _NonBlankName = Field(
        description="Tenant from the command envelope; required, never blank",
    )
    principal_id: _NonBlankName | None = Field(
        default=None,
        description="Authenticated principal, when the bus propagates one",
    )
    principal_authenticated: bool = Field(
        default=False,
        description="Whether principal_id was authenticated rather than asserted",
    )
