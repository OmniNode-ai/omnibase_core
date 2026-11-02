# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Identifier and digest patterns shared by the view policy and receipt models (OMN-21999).

Ids are semantic labels (letters, digits, ``_ . : -``, up to 128 characters, not
starting with a separator); digests are ``sha256:<64 lowercase hex>``.
"""

from typing import Annotated

from pydantic import StringConstraints

__all__ = ["VIEW_DIGEST_PATTERN", "VIEW_ID_PATTERN", "ViewDigest", "ViewId"]

VIEW_ID_PATTERN: str = r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"
VIEW_DIGEST_PATTERN: str = r"^sha256:[0-9a-f]{64}$"

ViewId = Annotated[str, StringConstraints(pattern=VIEW_ID_PATTERN)]
ViewDigest = Annotated[str, StringConstraints(pattern=VIEW_DIGEST_PATTERN)]
