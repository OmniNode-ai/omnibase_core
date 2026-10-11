# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Here-document tokens split out of handler_shell_words for OMN-20685."""

from __future__ import annotations

from omniclaude.nodes.node_git_effect.enums.enum_quote_kind import EnumQuoteKind
from omniclaude.nodes.node_git_effect.handlers.handler_shell_word import Word, WordPart


class HereDoc:
    """A here-document, placed where its ``<<`` operator was.

    The body is filled in when the tokenizer reaches it, on the lines after the
    command. ``expands`` is False when any part of the delimiter was quoted,
    in which case the shell expands nothing inside the body.
    """

    def __init__(self, strip_tabs: bool) -> None:
        self.strip_tabs = strip_tabs
        self.delimiter = ""
        self.expands = True
        self.body = ""

    def as_word(self) -> Word:
        """The body as a word, quoted the way the shell reads it."""
        return Word(
            (
                WordPart(
                    self.body,
                    EnumQuoteKind.DOUBLE if self.expands else EnumQuoteKind.LITERAL,
                ),
            )
        )
