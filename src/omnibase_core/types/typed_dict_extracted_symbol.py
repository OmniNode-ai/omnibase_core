# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from typing import NotRequired, TypedDict


class TypedDictExtractedSymbol(TypedDict):
    kind: str
    signature: str
    body_hash: str
    start_line: int
    end_line: int
    name: NotRequired[str]
