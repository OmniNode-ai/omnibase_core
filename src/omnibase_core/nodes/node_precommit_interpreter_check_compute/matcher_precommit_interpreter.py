# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure shell command matching, preserving the infra interpreter gate."""

from __future__ import annotations

import contextlib
import re
import shlex
from pathlib import PurePosixPath
from typing import cast

import yaml
from yaml.nodes import MappingNode, Node, SequenceNode

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.precommit_interpreter_check.model_precommit_raw_document import (
    ModelPrecommitRawDocument,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

VALIDATOR_ID = "precommit-interpreter-resolution"
SUPPRESS_MARKER = "precommit-" + "interp-ok"
SUPPRESS_MARKER_RE = re.compile(r"#[\s]*precommit-" + r"interp-ok:[\s]*\S")


LOCAL_LANGUAGES = {"system", "script"}

ENTRY_BANNED = {"python", "python3"}

_ASSIGN = "(?:[A-Za-z_]\\w*=(?:\"[^\"]*\"|'[^']*'|\\S*)\\s+)*"

_CMD_PREFIX = "(?:^|[;&|(`!]|\\$\\(|\\b(?:if|then|else|elif|do|while|until|exec|command|nice|time|env|xargs)\\s)"

SCRIPT_BANNED_RE = re.compile(_CMD_PREFIX + "\\s*" + _ASSIGN + "python(?![\\w./-])")

_ENV_ASSIGN_RE = re.compile("^[A-Za-z_][A-Za-z0-9_]*=")

_COMMAND_SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", ";;"}

_WRAPPERS = {"env", "exec", "command", "nice", "time", "builtin"}

_UV_RUN_VALUE_OPTS = {
    "--with",
    "--with-editable",
    "--with-requirements",
    "--python",
    "-p",
    "--directory",
    "--project",
    "--package",
    "--index",
    "--default-index",
    "--index-url",
    "--extra-index-url",
    "--find-links",
    "-f",
    "--extra",
    "--group",
    "--only-group",
    "--no-group",
    "--config-file",
    "--cache-dir",
    "--refresh-package",
    "--resolution",
    "--prerelease",
    "--python-preference",
    "--color",
    "--env-file",
    "--constraints",
    "-c",
    "--overrides",
    "--no-binary-package",
    "--no-build-package",
}


def _shell_tokens(text: str) -> list[str]:
    """Tokenize a shell string, keeping operators (`&&`, `|`, `;`) as tokens.

    `shlex.split` collapses operators into the surrounding words, which would
    hide the second command of `bash -c 'true && python x.py'`.
    """
    lexer = shlex.shlex(text, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    return list(lexer)


def _split_segments(tokens: list[str]) -> list[list[str]]:
    """Split a token list into per-command segments on shell operators."""
    segments: list[list[str]] = [[]]
    for tok in tokens:
        if tok in _COMMAND_SEPARATORS:
            segments.append([])
        else:
            segments[-1].append(tok)
    return [seg for seg in segments if seg]


def _command_word(tokens: list[str]) -> str | None:
    """Return the interpreter a single command segment will actually exec.

    Sees through inline `FOO=bar` assignments, transparent wrappers (`env`,
    `exec`, ...) and a full `uv run [options]` prefix -- including options that
    consume a following value -- so the token reported is the one the shell will
    resolve on PATH. Returns None when `uv run` covers the command: uv resolves
    the project interpreter itself, which is the sanctioned form.
    """
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _WRAPPERS or _ENV_ASSIGN_RE.match(tok):
            i += 1
            continue
        if tok == "uv" and i + 1 < len(tokens) and (tokens[i + 1] == "run"):
            i += 2
            while i < len(tokens) and tokens[i].startswith("-"):
                opt = tokens[i]
                i += 1
                if "=" not in opt and opt in _UV_RUN_VALUE_OPTS:
                    i += 1
            return None
        return tok
    return None


def scan_entry(hook_id: str, entry: str) -> list[str]:
    """Return violation strings for one hook `entry:` value."""
    violations: list[str] = []
    if SUPPRESS_MARKER_RE.search(entry):
        return violations
    try:
        tokens = _shell_tokens(entry)
    except ValueError:
        return [f"{hook_id}: entry is not shell-parsable: {entry!r}"]
    fragments: list[list[str]] = [tokens]
    for idx, tok in enumerate(tokens):
        if (
            tok in {"bash", "sh", "zsh"}
            and idx + 2 < len(tokens)
            and (tokens[idx + 1] == "-c")
        ):
            with contextlib.suppress(ValueError):
                fragments.append(_shell_tokens(tokens[idx + 2]))
    for frag in fragments:
        for segment in _split_segments(frag):
            word = _command_word(segment)
            if word in ENTRY_BANNED:
                violations.append(
                    f"{hook_id}: entry invokes bare `{word}` -- use `uv run python` (macOS has no bare `python`; entry={entry!r})"
                )
    return violations


def _mapping(value: object) -> dict[str, object]:
    """Require the mapping shape the script expects from safe YAML."""
    if not isinstance(value, dict):
        raise ModelOnexError(
            message="pre-commit configuration must contain mappings",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return cast("dict[str, object]", value)


def _sequence(value: object) -> list[object]:
    """Treat false values as empty lists, as the script does."""
    if not value:
        return []
    if not isinstance(value, list):
        raise ModelOnexError(
            message="pre-commit repos and hooks must be lists",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return cast("list[object]", value)


def _child(node: Node | None, key: str) -> Node | None:
    """Resolve source locations with safe-load's mapping merge precedence."""
    if isinstance(node, MappingNode):
        for name, value in reversed(node.value):
            if name.value == key:
                return cast("Node", value)
        for name, value in node.value:
            if name.value != "<<":
                continue
            sources = value.value if isinstance(value, SequenceNode) else [value]
            for source in sources:
                child = _child(source, key)
                if child is not None:
                    return child
    return None


def _children(node: Node | None) -> list[Node]:
    """Extract source nodes corresponding to a list."""
    return list(node.value) if isinstance(node, SequenceNode) else []


def _load_document(source: str) -> dict[str, object]:
    """Read the ``repos`` key through a Pydantic model, keeping the script's errors."""
    try:
        document = load_yaml_content_as_model(source, ModelPrecommitRawDocument)
    except ModelOnexError as exc:
        prefix = "YAML parsing error: "
        if exc.message.startswith(prefix):
            raise yaml.YAMLError(exc.message[len(prefix) :]) from exc
        return _mapping(None)
    return {"repos": document.repos}


def eligible_entries(source: str) -> list[tuple[str, str, int]]:
    """Return eligible hook labels, entry text, and the entry's source line."""
    tree = yaml.compose(source, Loader=yaml.SafeLoader)
    if not isinstance(tree, MappingNode):
        _mapping(None)
    config = _load_document(source)
    repo_nodes = _children(_child(tree, "repos"))
    entries: list[tuple[str, str, int]] = []
    for repo_index, repo_value in enumerate(_sequence(config.get("repos"))):
        repo = _mapping(repo_value)
        repo_node = repo_nodes[repo_index]
        hook_nodes = _children(_child(repo_node, "hooks"))
        for hook_index, hook_value in enumerate(_sequence(repo.get("hooks"))):
            hook = _mapping(hook_value)
            entry = hook.get("entry")
            if not entry or hook.get("language", "system") not in LOCAL_LANGUAGES:
                continue
            if not isinstance(entry, str):
                raise ModelOnexError(
                    message="pre-commit hook entry must be a string",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            entry_node = _child(hook_nodes[hook_index], "entry")
            line = entry_node.start_mark.line + 1 if entry_node is not None else 1
            entries.append((str(hook.get("id", "<unnamed>")), entry, line))
    return entries


def referenced_scripts(entry: str, repository_root: str | None = None) -> list[str]:
    """Identify shell source labels without consulting the filesystem."""
    try:
        tokens = shlex.split(entry)
    except ValueError:
        return []
    paths = []
    for token in tokens:
        if not token.endswith((".sh", ".bash")):
            continue
        path = PurePosixPath(token)
        if repository_root is not None and path.is_absolute():
            root = PurePosixPath(repository_root)
            if path.is_relative_to(root):
                path = path.relative_to(root)
        paths.append(str(path))
    return paths


def scan_script(path: str, source: str) -> list[tuple[int, str]]:
    """Scan supplied shell text using the original command-position regex."""
    violations: list[tuple[int, str]] = []
    for line_number, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or SUPPRESS_MARKER_RE.search(line):
            continue
        if SCRIPT_BANNED_RE.search(line):
            violations.append(
                (
                    line_number,
                    f"{path}:{line_number}: invokes bare `python` -- use `uv run python` "
                    f"or a guarded `python3` ({stripped!r})",
                )
            )
    return violations
