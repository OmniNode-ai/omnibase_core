# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Redirection tokens split out of handler_shell_words for OMN-20685."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omniclaude.nodes.node_git_effect.handlers.handler_shell_word import Word


class Redirect:
    """A redirection, emitted only by ``tokenize(..., keep_redirects=True)``.

    ``op`` is the operator without its descriptor digits (``>``, ``>>``,
    ``<``, ``<<<``, ``&>``, ``>|``, ``>&``); ``fd`` is the digits glued before
    it (``"2"`` in ``2>err.log``) or ``None``; ``target`` is the word after it,
    or ``None`` when the operator takes none (``>&-``). A here-document is a
    :class:`HereDoc`, never a ``Redirect``.

    Most guards want redirections dropped, which is the default. A guard that
    has to know which file a command writes (OMN-19542: a body file written by
    an earlier segment of the same command) asks for them.
    """

    def __init__(self, op: str, fd: str | None) -> None:
        self.op = op
        self.fd = fd
        self.target: Word | None = None
