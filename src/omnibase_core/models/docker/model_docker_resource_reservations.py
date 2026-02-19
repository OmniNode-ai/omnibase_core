# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Docker Resource Reservations Model.

Resource reservations for Docker services.
"""

from pydantic import BaseModel, Field


class ModelDockerResourceReservations(BaseModel):
    """Resource reservations for Docker services."""

    cpus: str | None = Field(default=None, description="CPU reservation")
    memory: str | None = Field(default=None, description="Memory reservation")
