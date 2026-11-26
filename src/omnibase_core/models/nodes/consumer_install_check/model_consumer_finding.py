# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One import or collection failure of a consumer, named three ways (OMN-26670)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelConsumerFinding(BaseModel):
    """Consumer, import and missing name: the three the failure must always carry."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    consumer: str = Field(min_length=1)
    stage: str = Field(min_length=1, description="'entry-point' or 'collection'")
    import_statement: str = Field(
        min_length=1, description="The failing import, with file and line when known"
    )
    missing_name: str = Field(min_length=1)
    detail: str = Field(default="", description="Entry point or test path that hit it")
    attributed_to_candidate: bool

    def render(self) -> str:
        """One line naming consumer, import and missing name."""
        return (
            f"consumer={self.consumer} import={self.import_statement!r} "
            f"missing={self.missing_name} stage={self.stage} "
            f"candidate_related={str(self.attributed_to_candidate).lower()}"
            + (f" at={self.detail}" if self.detail else "")
        )
