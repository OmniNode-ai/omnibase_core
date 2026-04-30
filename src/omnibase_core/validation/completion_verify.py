# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import re

_BACKTICK = re.compile(r"`([A-Za-z_][\w.]*)`")
_CAMEL = re.compile(r"\b([a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*)\b")
_PASCAL_TOKEN = re.compile(r"\b([A-Z][a-zA-Z0-9]*)\b")
_DOTTED = re.compile(r"\b([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){2,})\b")


def _is_pascal_identifier(value: str) -> bool:
    return len(value) >= 3 and sum(char.isupper() for char in value) >= 2


def extract_identifiers(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for pat in (_BACKTICK, _CAMEL):
        for m in pat.findall(text):
            if m not in seen:
                seen.add(m)
                out.append(m)
    for m in _PASCAL_TOKEN.findall(text):
        if _is_pascal_identifier(m) and m not in seen:
            seen.add(m)
            out.append(m)
    for m in _DOTTED.findall(text):
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out
