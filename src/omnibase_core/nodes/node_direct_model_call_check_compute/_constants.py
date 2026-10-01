# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Sink tables, shell grammar and limits shared by the direct-model-call analysis (OMN-20295)."""

from __future__ import annotations

import ast
import re
from typing import Final

_UNKNOWN: Final[str] = "{?}"


_TEXT_CAP: Final[int] = 16


_SUMMARY_DEPTH: Final[int] = 4


_FIXPOINT_ROUNDS: Final[int] = 6


_MODULE: Final[str] = "<module>"


_SCRIPT: Final[str] = "<script>"


_PYTHON_SUFFIXES: Final[tuple[str, ...]] = (".py", ".pyi")


_SHELL_SUFFIXES: Final[tuple[str, ...]] = (".sh", ".bash")


_EXEC_FIRST_ARG: Final[frozenset[str]] = frozenset(
    {
        "subprocess.run",
        "subprocess.Popen",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "subprocess.getoutput",
        "subprocess.getstatusoutput",
        "os.system",
        "os.popen",
        "asyncio.create_subprocess_shell",
        "pexpect.spawn",
        "pexpect.run",
        "pexpect.popen_spawn.PopenSpawn",
    }
)


_EXEC_POSITIONAL: Final[frozenset[str]] = frozenset(
    {"asyncio.create_subprocess_exec", "os.execl", "os.execlp", "os.execle"}
)


_EXEC_SECOND_ARG: Final[frozenset[str]] = frozenset(
    {
        "os.execv",
        "os.execvp",
        "os.execve",
        "os.execvpe",
        "os.posix_spawn",
        "os.posix_spawnp",
    }
)


_EXEC_THIRD_ARG: Final[frozenset[str]] = frozenset(
    {"os.spawnv", "os.spawnve", "os.spawnvp", "os.spawnvpe"}
)


_EXEC_ARG_KEYWORDS: Final[tuple[str, ...]] = ("args", "cmd", "command", "argv")


_HTTP_FUNCTIONS: Final[frozenset[str]] = frozenset(
    {
        f"{module}.{verb}"
        for module in ("httpx", "requests", "requests.api")
        for verb in ("get", "post", "put", "patch", "delete", "request", "stream")
    }
    | {
        "urllib.request.urlopen",
        "urllib.request.Request",
        "aiohttp.request",
        "http.client.HTTPConnection",
        "http.client.HTTPSConnection",
        "urllib3.request",
    }
)


_HTTP_METHODS: Final[frozenset[str]] = frozenset(
    {"post", "put", "patch", "request", "stream", "get", "send", "ws_connect"}
)


_HTTP_VERBS: Final[frozenset[str]] = frozenset(
    {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
)


_HTTP_CLIENT_MODULES: Final[tuple[str, ...]] = (
    "httpx",
    "requests",
    "aiohttp",
    "urllib.request",
    "urllib3",
    "http.client",
    "httpcore",
)


_BODY_KEYWORDS: Final[tuple[str, ...]] = ("json", "data", "content", "body")


_SHELL_FUNCTION: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_:-]*)\s*\(\s*\)\s*\{?\s*$"
)


_SHELL_ASSIGN: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:export\s+|local\s+|readonly\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$"
)


_SHELL_VAR: Final[re.Pattern[str]] = re.compile(
    r"\$\{?([A-Za-z_][A-Za-z0-9_]*)(?::?-[^}]*)?\}?"
)


_MODEL_SERVER_ROUTE: Final[re.Pattern[str]] = re.compile(r"/(?:models|props|slots)/?$")


_SHELL_KEYWORDS: Final[frozenset[str]] = frozenset(
    {"{", "}", "then", "do", "done", "else", "elif", "if", "fi", "while", "until", "!"}
)


_NESTED_COMMAND: Final[re.Pattern[str]] = re.compile(r";|&&|\|\||\||\n")


_ENV_ASSIGN_TOKEN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


_WORD: Final[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


_Event = tuple[str, ast.AST | str | None]
