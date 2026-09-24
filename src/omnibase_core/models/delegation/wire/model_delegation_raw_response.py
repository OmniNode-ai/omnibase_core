# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The provider's own answer, kept byte for byte beside what the caller got.

OMN-19385 (K5 of OMN-18925). The runtime extracts a deliverable from the
provider response on purpose, so the text a caller receives is not always the
text the provider returned. The D1 output-only release bar (OMN-18932) needs
both to decide whether extraction was required, and before this carrier only
the extracted text left the runtime. For a JSON deliverable that made text
after the value unobservable.

What is kept is exactly one provider field, the message content the runtime
extracts from, and its identity. Nothing else from the provider body, and never
a request header, a credential or the request payload. The content is model
output; any text the caller put in the prompt it echoes is already in the
caller's own request.

The text is bounded. A response over :data:`MAX_RAW_RESPONSE_UTF8_BYTES` keeps
its hash and length and drops the text, and a reader must treat that as "not
retained" rather than as evidence either way.
"""

from __future__ import annotations

import hashlib
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: Upper bound on the retained text, in UTF-8 bytes. A delegation terminal also
#: carries the prompt and the extracted answer, and the whole event must fit a
#: broker message; 64 KiB keeps a typical answer whole with room to spare.
MAX_RAW_RESPONSE_UTF8_BYTES: int = 65536


class ModelDelegationRawResponse(BaseModel):
    """One provider response's content, exactly, with its hash and length."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_field: str = Field(
        min_length=1,
        description=(
            "The provider body field the text was read from, e.g. "
            "'choices[0].message.content'."
        ),
    )
    sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
        description="Lowercase hex SHA-256 of the full content's UTF-8 bytes.",
    )
    utf8_bytes: int = Field(
        ge=0, description="Length of the full content in UTF-8 bytes."
    )
    text: str | None = Field(
        description=(
            "The content exactly as the provider returned it, or None when it "
            "exceeds MAX_RAW_RESPONSE_UTF8_BYTES."
        ),
    )

    @property
    def retained(self) -> bool:
        """Whether the text itself, not only its identity, was kept."""
        return self.text is not None

    @classmethod
    def from_provider_content(cls, content: str, *, source_field: str) -> Self:
        """Build the carrier for *content*, dropping the text over the bound."""
        encoded = content.encode("utf-8")
        return cls(
            source_field=source_field,
            sha256=hashlib.sha256(encoded).hexdigest(),
            utf8_bytes=len(encoded),
            text=content if len(encoded) <= MAX_RAW_RESPONSE_UTF8_BYTES else None,
        )

    @model_validator(mode="after")
    def _text_matches_its_identity(self) -> Self:
        if self.text is None:
            if self.utf8_bytes <= MAX_RAW_RESPONSE_UTF8_BYTES:
                raise ValueError(
                    "text may be omitted only when the content exceeds the "
                    f"{MAX_RAW_RESPONSE_UTF8_BYTES}-byte bound"
                )
            return self
        encoded = self.text.encode("utf-8")
        if len(encoded) > MAX_RAW_RESPONSE_UTF8_BYTES:
            raise ValueError(
                f"text exceeds the {MAX_RAW_RESPONSE_UTF8_BYTES}-byte bound; "
                "keep only its sha256 and utf8_bytes"
            )
        if len(encoded) != self.utf8_bytes:
            raise ValueError("utf8_bytes does not match the text's UTF-8 length")
        if hashlib.sha256(encoded).hexdigest() != self.sha256:
            raise ValueError("sha256 does not match the text")
        return self


__all__ = ["MAX_RAW_RESPONSE_UTF8_BYTES", "ModelDelegationRawResponse"]
