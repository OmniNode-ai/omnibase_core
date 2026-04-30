# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict


class ModelEscalationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    severity_level: int
    guidance: str
    telemetry: dict[str, object] | None = None
