# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One extracted markdown link."""

from pydantic import BaseModel, ConfigDict


class ModelMarkdownLink(BaseModel):
    """Line and display text preserve the original CLI diagnostics."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    url: str
    text: str
    line_number: int
    source_file: str

    @property
    def is_missing_reference(self) -> bool:
        return self.url.startswith("__ONEX_MISSING_REF__")

    @property
    def missing_reference_name(self) -> str | None:
        if not self.is_missing_reference:
            return None
        return self.url[len("__ONEX_MISSING_REF__") + 1 :]

    @property
    def display_link(self) -> str:
        if self.is_missing_reference:
            return f"[{self.text}][{self.missing_reference_name}]"
        return f"[{self.text}]({self.url})"
