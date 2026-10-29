# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Per-line views of a scanned file: code with comments and docstrings removed, and its literals.

Pure text work shared by the hardcoded model-configuration scanner and the K6 literal
checker (OMN-21537). Python is tokenised, so a comment is blanked and a string that opens
a statement (a docstring or a bare expression) is prose; other text forms are judged line
by line on text with their comments removed.
"""

from __future__ import annotations

import io
import re
import tokenize
from collections.abc import Collection, Sequence
from functools import lru_cache

__all__ = [
    "file_suffix",
    "generic_views",
    "glob_regex",
    "python_views",
    "strip_comment",
]


def file_suffix(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    dot = name.rfind(".")
    return name[dot:].lower() if dot > 0 else ""


def _strip_hash_comment(line: str) -> str:
    quote = ""
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1].isspace()):
            return line[:i]
    return line


def _strip_slash_comment(line: str) -> str:
    stripped = line.lstrip()
    if stripped.startswith(("/*", "*")):
        return ""
    quote = ""
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in ("'", '"', "`"):
            quote = ch
        elif line.startswith("//", i) and (i == 0 or line[i - 1] != ":"):
            return line[:i]
    return line


def _blank(code: dict[int, str], start: tuple[int, int], end: tuple[int, int]) -> None:
    (srow, scol), (erow, ecol) = start, end
    for row in range(srow, erow + 1):
        line = code.get(row, "")
        lo = scol if row == srow else 0
        hi = ecol if row == erow else len(line)
        code[row] = line[:lo] + " " * max(hi - lo, 0) + line[hi:]


def python_views(
    text: str, lines: Sequence[str]
) -> tuple[dict[int, str], dict[int, list[str]]] | None:
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError):
        return None
    code = dict(enumerate(lines, start=1))
    literals: dict[int, list[str]] = {}
    prev_type: int | None = None
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            _blank(code, tok.start, tok.end)
            continue
        if tok.type in (tokenize.NL, tokenize.ENCODING):
            continue
        if tok.type == tokenize.STRING:
            if prev_type is None or prev_type in (
                tokenize.NEWLINE,
                tokenize.INDENT,
                tokenize.DEDENT,
            ):
                # A string that opens a statement is a docstring or a bare
                # expression: prose, not configuration.
                _blank(code, tok.start, tok.end)
            else:
                for offset, part in enumerate(tok.string.split("\n")):
                    literals.setdefault(tok.start[0] + offset, []).append(part)
        elif tok.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
            for offset, part in enumerate(tok.string.split("\n")):
                literals.setdefault(tok.start[0] + offset, []).append(part)
        prev_type = tok.type
    return code, literals


def strip_comment(
    path: str,
    line: str,
    slash_suffixes: Collection[str],
    no_comment_suffixes: Collection[str],
) -> str:
    """``line`` without its comment, by the comment style of ``path``'s suffix."""
    suffix = file_suffix(path)
    if suffix in no_comment_suffixes:
        return line
    if suffix in slash_suffixes:
        return _strip_slash_comment(line)
    return _strip_hash_comment(line)


def generic_views(
    path: str,
    lines: Sequence[str],
    slash_suffixes: Collection[str],
    no_comment_suffixes: Collection[str],
) -> tuple[dict[int, str], dict[int, list[str]]]:
    code = {
        n: strip_comment(path, line, slash_suffixes, no_comment_suffixes)
        for n, line in enumerate(lines, start=1)
    }
    # Outside Python every value on a line is a candidate literal.
    literals = {n: [text] for n, text in code.items() if text.strip()}
    return code, literals


@lru_cache(maxsize=512)
def glob_regex(glob: str) -> re.Pattern[str]:
    """Translate a repository glob: ``**/`` spans zero or more directories,
    ``**`` spans anything, ``*`` and ``?`` stay within one path segment."""
    out: list[str] = []
    i = 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")
