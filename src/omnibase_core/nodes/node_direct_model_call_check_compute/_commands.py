# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Command lines and request bodies, shared by Python exec sinks and shell files (OMN-20295)."""

from __future__ import annotations

import shlex
from collections.abc import Iterable, Sequence

from omnibase_core.enums.enum_direct_model_call_kind import EnumDirectModelCallKind
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_policy import (
    ModelDirectModelCallPolicy,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._constants import (
    _ENV_ASSIGN_TOKEN,
    _MODEL_SERVER_ROUTE,
    _SHELL_KEYWORDS,
    _UNKNOWN,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._hit import _Hit
from omnibase_core.nodes.node_direct_model_call_check_compute._policy_patterns import (
    _compile,
    _program_name,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._script_ref import (
    _ScriptRef,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._shell_state import (
    _ShellState,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._value import _Val


def _url_hits(policy: ModelDirectModelCallPolicy, url: _Val, where: str) -> list[_Hit]:
    compiled = _compile(policy)
    for text in sorted(url.texts):
        if compiled.provider_host.search(text):
            return [
                _Hit(
                    EnumDirectModelCallKind.HTTP,
                    "http",
                    f"{where}: URL {text!r} is a model provider",
                )
            ]
        if compiled.model_api_path.search(text):
            return [
                _Hit(
                    EnumDirectModelCallKind.HTTP,
                    "http",
                    f"{where}: URL {text!r} is a model API path",
                )
            ]
    if "base_url" in url.labels:
        return [
            _Hit(
                EnumDirectModelCallKind.HTTP,
                "http",
                f"{where}: URL derives from a model base URL",
            )
        ]
    if "base_url_weak" in url.labels and any(
        _MODEL_SERVER_ROUTE.search(t) for t in url.texts
    ):
        return [
            _Hit(
                EnumDirectModelCallKind.HTTP,
                "http",
                f"{where}: URL is a model-server route of a base_url",
            )
        ]
    if "base_url_weak" in url.labels:
        # A plain base_url is also a GitHub, gateway or ledger client's. It is
        # a model call only in a file that already holds a model call.
        return [
            _Hit(
                EnumDirectModelCallKind.HTTP,
                "http",
                f"{where}: URL derives from a base_url",
                weak=True,
            )
        ]
    return []


def _body_hits(
    policy: ModelDirectModelCallPolicy, body: _Val, where: str
) -> list[_Hit]:
    keys = body.keys | frozenset(k for e in (body.seq or ()) for k in e.keys)
    model_keys = keys & frozenset(policy.payload_keys)
    if model_keys:
        names = ", ".join(sorted(model_keys))
        return [
            _Hit(
                EnumDirectModelCallKind.HTTP,
                "http",
                f"{where}: request body carries {names}",
            )
        ]
    if "model" in keys and keys & frozenset(policy.payload_model_companions):
        return [
            _Hit(
                EnumDirectModelCallKind.HTTP,
                "http",
                f"{where}: request body is a model request",
            )
        ]
    return []


def _text_body_hits(
    policy: ModelDirectModelCallPolicy, texts: Iterable[str], where: str
) -> list[_Hit]:
    for text in texts:
        for key in policy.payload_keys:
            if f'"{key}"' in text or f"'{key}'" in text:
                return [
                    _Hit(
                        EnumDirectModelCallKind.HTTP,
                        "http",
                        f"{where}: request body carries {key}",
                    )
                ]
    return []


def _split_shell(
    text: str, state: _ShellState | None = None
) -> list[list[frozenset[str]]]:
    """The simple commands of a shell line: quote-aware, operator-aware, with
    case patterns and redirect targets dropped."""
    state = state if state is not None else _ShellState()
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    lexer.commenters = "#"
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = text.split()
    commands: list[list[frozenset[str]]] = []
    current: list[str] = []
    skip_next = False

    def flush() -> None:
        if current:
            commands.append([frozenset({t}) for t in current])
        current.clear()

    for index, token in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue
        if state.expecting_pattern:
            if token == ")":
                state.expecting_pattern = False
            elif token == "esac":
                state.in_case = state.expecting_pattern = False
            continue
        if token and all(c in ";&|()<>" for c in token):
            if token.startswith(("<", ">")) or token.endswith((">", "<")):
                if token in {"<<", "<<-"} and index + 1 < len(tokens):
                    state.heredoc = tokens[index + 1].strip("'\"")
                skip_next = True
                continue
            flush()
            if state.in_case and token.startswith(";;"):
                state.expecting_pattern = True
            continue
        if not current and token in _SHELL_KEYWORDS:
            continue
        if not current and token == "case":
            state.in_case = True
        if state.in_case and token == "in" and current and current[0] == "case":
            current.clear()
            state.expecting_pattern = True
            continue
        if not current and token == "esac":
            state.in_case = False
            continue
        current.append(token)
    flush()
    return commands


def _is_wrapper_option(token: str) -> bool:
    """A token a command wrapper consumes before the program it runs."""
    if token.startswith("-") or token in {"run", "exec", "--", "tool"}:
        return True
    return bool(_ENV_ASSIGN_TOKEN.match(token)) or token.rstrip("smhd").isdigit()


def _command_hits(
    policy: ModelDirectModelCallPolicy,
    positions: Sequence[_Val],
    refs: list[_ScriptRef],
    depth: int = 0,
) -> list[_Hit]:
    """Judge one command line, given the possible values at each argv position."""
    if not positions or depth > 6:
        return []
    head = positions[0]
    rest = positions[1:]
    rest_texts = [t for p in rest for t in p.texts]
    hits: list[_Hit] = []
    candidates = sorted(head.texts)
    if "python" in head.labels:
        candidates.append("python")
    for candidate in candidates:
        if candidate == _UNKNOWN:
            continue
        program = _program_name(candidate)
        if program in policy.model_clis:
            hits.append(
                _Hit(
                    EnumDirectModelCallKind.CLI_EXEC,
                    program,
                    f"executes the model CLI {program}",
                )
            )
        elif program in policy.print_mode_clis:
            if any(t in policy.print_flags for t in rest_texts):
                hits.append(
                    _Hit(
                        EnumDirectModelCallKind.CLI_EXEC,
                        program,
                        f"executes {program} in print mode",
                    )
                )
        elif program in policy.http_clis:
            for position in rest:
                hits.extend(_url_hits(policy, position, program))
            hits.extend(_text_body_hits(policy, rest_texts, program))
        elif program in policy.command_wrappers:
            index = 1
            while index < len(positions):
                texts = positions[index].texts
                if texts and all(_is_wrapper_option(t) for t in texts):
                    index += 1
                    continue
                break
            hits.extend(_command_hits(policy, positions[index:], refs, depth + 1))
        elif program in policy.shells:
            for index, position in enumerate(rest):
                if any(t.startswith("-") and "c" in t for t in position.texts):
                    if index + 1 < len(rest):
                        for text in sorted(rest[index + 1].texts):
                            for command in _split_shell(text):
                                hits.extend(
                                    _command_hits(
                                        policy,
                                        [_Val(texts=p) for p in command],
                                        refs,
                                        depth + 1,
                                    )
                                )
                    break
        elif program in policy.python_programs or program.startswith("python3."):
            for index, position in enumerate(rest):
                if "-m" in position.texts and index + 1 < len(rest):
                    for text in rest[index + 1].texts:
                        refs.append(_ScriptRef(text, is_module=True))
                    break
                scripts = [t for t in position.texts if t.endswith(".py")]
                if scripts:
                    refs.extend(_ScriptRef(t, is_module=False) for t in scripts)
                    break
    return hits


def _argv_hits(
    policy: ModelDirectModelCallPolicy, argv: _Val, refs: list[_ScriptRef]
) -> list[_Hit]:
    if argv.seq is not None:
        return _command_hits(policy, argv.seq, refs)
    hits: list[_Hit] = []
    for text in sorted(argv.texts):
        for command in _split_shell(text):
            hits.extend(_command_hits(policy, [_Val(texts=p) for p in command], refs))
    return hits
