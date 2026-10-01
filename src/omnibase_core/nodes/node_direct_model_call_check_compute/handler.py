# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerDirectModelCallCompute: a structural gate on direct model calls.

OMN-20295, task N4.1 of knowledge-base-internal
``beta/plans/2026-09-24-delegation-work-plan.md`` section 3.9. A model call
must sit inside the sanctioned delegation node packages named in
``policy.yaml``. Everywhere else it is refused, whatever words it uses.

The audit of 2026-10-01 (knowledge-base-internal
``reports/2026-10-01-gates-and-delegation-readiness-audit.md`` section 2) found
that the earlier gates matched banned literals: a crush shell-out, or a direct
call with no IP, model name or endpoint literal, passed all of them. This
handler reads the AST and the repository's import and call graph instead:

* **Sinks.** A process exec (``subprocess``, ``os.exec*``/``spawn*``/``system``,
  ``asyncio.create_subprocess_*``, ``pexpect``, and every command line of a
  shell file), an HTTP send (an ``httpx``/``requests``/``aiohttp``/``urllib``/
  ``http.client`` call, a ``.post``/``.request``/``.stream`` method, or a
  ``curl``/``wget`` exec), and the import of a model provider SDK.
* **Values.** Each argument is resolved through local and module assignments,
  f-strings, concatenation, ``join``, ``os.path.join``/``urljoin``,
  ``os.environ``/``getenv`` reads, ``shlex.split``, ``shutil.which`` and the
  return values of the repository's own functions, with their parameters
  substituted at each call site.
* **Signals.** An exec is a model call when its program resolves to a model CLI
  (``claude`` only with a print flag), after unwrapping ``env``/``timeout``/
  ``uv run`` and ``sh -c``. An HTTP send is a model call when its URL resolves
  to a model API path or a provider host, or derives from a base-URL source,
  or when its body is a model request (``messages``, or ``model`` with a
  prompt-shaped key).
* **Parameter sinks.** A function whose parameter reaches a sink unresolved
  passes the check to its callers, across files, so a wrapper such as
  ``request_json(url, body)`` is judged at each call with the caller's values.
* **Call graph.** A function that calls a model-calling function in another
  file is a ``call_via`` site, transitively; a file that executes a
  model-calling file of the repository (``python x.py``, ``uv run x.py``) is an
  ``exec_via`` site. A new caller of a baselined site is therefore a new site.

Everything here is PURE and DETERMINISTIC: no filesystem, network, environment
or clock I/O. No inline suppression marker is honoured; ``policy.yaml`` is the
only place a sanctioned package is named.

A call whose URL and body are both opaque at every level (read from a file,
built from runtime data) cannot be seen by any static gate. The backstop for
those is OMN-20299: server-side reconciliation of every model-server request
against a ``delegation_events`` run.
"""

from __future__ import annotations

import ast
import posixpath
import re
import shlex
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from functools import lru_cache
from typing import Final

from omnibase_core.nodes.node_direct_model_call_check_compute.models import (
    LiteralDirectModelCallKind,
    ModelDirectModelCallBaselineEntry,
    ModelDirectModelCallFinding,
    ModelDirectModelCallPolicy,
    ModelDirectModelCallScanInput,
    ModelDirectModelCallSourceFile,
)

__all__ = [
    "HandlerDirectModelCallCompute",
    "ModelDirectModelCallComparison",
    "added_entries",
    "compare_with_baseline",
    "entry_problems",
    "is_sanctioned",
    "scan",
]

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


# ---------------------------------------------------------------------------
# Abstract values
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Val:
    """What an expression may evaluate to, as far as the gate needs to know.

    ``texts`` are the possible string renderings, with ``{?}`` for an unknown
    piece. ``labels`` carry ``base_url`` (derived from a base-URL source) and
    ``python`` (the running interpreter). ``keys`` are dict keys when the value
    is a mapping. ``seq`` holds the elements of a literal list or tuple.
    ``params`` names the enclosing function's parameters the value derives from.
    """

    texts: frozenset[str] = frozenset()
    labels: frozenset[str] = frozenset()
    keys: frozenset[str] = frozenset()
    seq: tuple[_Val, ...] | None = None
    params: frozenset[str] = frozenset()


_EMPTY: Final[_Val] = _Val()
_OPAQUE: Final[_Val] = _Val(texts=frozenset({_UNKNOWN}))


def _cap(texts: Iterable[str]) -> frozenset[str]:
    ordered = sorted(set(texts))
    return frozenset(ordered[:_TEXT_CAP])


def _join(*vals: _Val) -> _Val:
    present = [v for v in vals if v is not _EMPTY]
    if not present:
        return _EMPTY
    if len(present) == 1:
        return present[0]
    seqs = [v.seq for v in present if v.seq is not None]
    seq: tuple[_Val, ...] | None = None
    if seqs:
        width = max(len(s) for s in seqs)
        seq = tuple(_join(*(s[i] for s in seqs if i < len(s))) for i in range(width))
    return _Val(
        texts=_cap(t for v in present for t in v.texts),
        labels=frozenset(lab for v in present for lab in v.labels),
        keys=frozenset(k for v in present for k in v.keys),
        seq=seq,
        params=frozenset(p for v in present for p in v.params),
    )


def _concat(*vals: _Val) -> _Val:
    texts: set[str] = {""}
    for val in vals:
        pieces = val.texts or frozenset({_UNKNOWN})
        texts = {left + right for left in texts for right in pieces}
        if len(texts) > _TEXT_CAP:
            texts = set(sorted(texts)[:_TEXT_CAP])
    return _Val(
        texts=frozenset(texts),
        labels=frozenset(lab for v in vals for lab in v.labels),
        keys=frozenset(),
        params=frozenset(p for v in vals for p in v.params),
    )


def _flatten(val: _Val) -> _Val:
    """Drop the sequence structure, keeping every element's facts."""
    if val.seq is None:
        return val
    return _Val(
        texts=val.texts,
        labels=val.labels | frozenset(lab for e in val.seq for lab in e.labels),
        keys=val.keys,
        params=val.params | frozenset(p for e in val.seq for p in e.params),
    )


def _substitute(val: _Val, binding: dict[str, _Val]) -> _Val:
    """Replace parameter references in a callee's value by the caller's values."""
    seq = (
        tuple(_substitute(e, binding) for e in val.seq) if val.seq is not None else None
    )
    own = _Val(texts=val.texts, labels=val.labels, keys=val.keys, seq=seq)
    bound = [binding[p] for p in sorted(val.params) if p in binding]
    if not bound:
        return own
    if not val.texts and not val.labels and not val.keys and seq is None:
        return _join(*bound)
    return _join(own, *bound)


# ---------------------------------------------------------------------------
# Policy helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Compiled:
    model_api_path: re.Pattern[str]
    provider_host: re.Pattern[str]
    base_url_identifier: re.Pattern[str]
    generic_base_url_identifier: re.Pattern[str]
    model_env_key: re.Pattern[str]


def _compile(policy: ModelDirectModelCallPolicy) -> _Compiled:
    return _compile_patterns(
        policy.model_api_path_pattern,
        policy.provider_host_pattern,
        policy.base_url_identifier_pattern,
        policy.generic_base_url_identifier_pattern,
        policy.model_env_key_pattern,
    )


@lru_cache(maxsize=8)
def _compile_patterns(
    model_api_path: str,
    provider_host: str,
    base_url_identifier: str,
    generic_base_url_identifier: str,
    model_env_key: str,
) -> _Compiled:
    return _Compiled(
        model_api_path=re.compile(model_api_path),
        provider_host=re.compile(provider_host),
        base_url_identifier=re.compile(base_url_identifier),
        generic_base_url_identifier=re.compile(generic_base_url_identifier),
        model_env_key=re.compile(model_env_key),
    )


@lru_cache(maxsize=256)
def _glob_regex(glob: str) -> re.Pattern[str]:
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


def is_sanctioned(policy: ModelDirectModelCallPolicy, repo: str, path: str) -> bool:
    """True when ``path`` sits inside one of ``repo``'s sanctioned packages."""
    return any(
        _glob_regex(glob).match(path)
        for glob in policy.sanctioned_packages.get(repo, ())
    )


def _name_labels(
    compiled: _Compiled, name: str, env_key: bool = False
) -> frozenset[str]:
    """``base_url`` for a name of a model endpoint, ``base_url_weak`` for a
    plain base URL, nothing otherwise."""
    if compiled.base_url_identifier.search(name) or (
        env_key and compiled.model_env_key.search(name)
    ):
        return frozenset({"base_url"})
    if compiled.generic_base_url_identifier.search(name):
        return frozenset({"base_url_weak"})
    return frozenset()


def _program_name(text: str) -> str:
    stripped = text.strip().strip("'\"")
    return posixpath.basename(stripped)


# ---------------------------------------------------------------------------
# Command lines (shared by Python exec sinks and shell files)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Hit:
    kind: LiteralDirectModelCallKind
    target: str
    evidence: str
    weak: bool = False


@dataclass(frozen=True)
class _ScriptRef:
    """A command line that runs a file or module of the repository."""

    name: str
    is_module: bool


def _url_hits(policy: ModelDirectModelCallPolicy, url: _Val, where: str) -> list[_Hit]:
    compiled = _compile(policy)
    for text in sorted(url.texts):
        if compiled.provider_host.search(text):
            return [_Hit("http", "http", f"{where}: URL {text!r} is a model provider")]
        if compiled.model_api_path.search(text):
            return [_Hit("http", "http", f"{where}: URL {text!r} is a model API path")]
    if "base_url" in url.labels:
        return [_Hit("http", "http", f"{where}: URL derives from a model base URL")]
    if "base_url_weak" in url.labels and any(
        _MODEL_SERVER_ROUTE.search(t) for t in url.texts
    ):
        return [
            _Hit("http", "http", f"{where}: URL is a model-server route of a base_url")
        ]
    if "base_url_weak" in url.labels:
        # A plain base_url is also a GitHub, gateway or ledger client's. It is
        # a model call only in a file that already holds a model call.
        return [
            _Hit("http", "http", f"{where}: URL derives from a base_url", weak=True)
        ]
    return []


def _body_hits(
    policy: ModelDirectModelCallPolicy, body: _Val, where: str
) -> list[_Hit]:
    keys = body.keys | frozenset(k for e in (body.seq or ()) for k in e.keys)
    model_keys = keys & frozenset(policy.payload_keys)
    if model_keys:
        names = ", ".join(sorted(model_keys))
        return [_Hit("http", "http", f"{where}: request body carries {names}")]
    if "model" in keys and keys & frozenset(policy.payload_model_companions):
        return [_Hit("http", "http", f"{where}: request body is a model request")]
    return []


def _text_body_hits(
    policy: ModelDirectModelCallPolicy, texts: Iterable[str], where: str
) -> list[_Hit]:
    for text in texts:
        for key in policy.payload_keys:
            if f'"{key}"' in text or f"'{key}'" in text:
                return [_Hit("http", "http", f"{where}: request body carries {key}")]
    return []


@dataclass
class _ShellState:
    """Shell syntax that spans lines: a case statement and a heredoc body."""

    in_case: bool = False
    expecting_pattern: bool = False
    heredoc: str | None = None


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
            hits.append(_Hit("cli_exec", program, f"executes the model CLI {program}"))
        elif program in policy.print_mode_clis:
            if any(t in policy.print_flags for t in rest_texts):
                hits.append(
                    _Hit("cli_exec", program, f"executes {program} in print mode")
                )
        elif program in policy.http_clis:
            for position in rest:
                hits.extend(_url_hits(policy, position, program))
            hits.extend(_text_body_hits(policy, rest_texts, program))
        elif program in policy.command_wrappers:
            index = 1
            while index < len(positions):
                texts = positions[index].texts
                if texts and all(
                    t.startswith("-")
                    or _ENV_ASSIGN_TOKEN.match(t)
                    or t in {"run", "exec", "--", "tool"}
                    or t.rstrip("smhd").isdigit()
                    for t in texts
                ):
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


# ---------------------------------------------------------------------------
# Python analysis
# ---------------------------------------------------------------------------


@dataclass
class _Summary:
    """What a repository function means to its callers."""

    params: tuple[str, ...]
    is_method: bool
    returns: _Val = _EMPTY
    param_sinks: dict[str, frozenset[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class _Site:
    path: str
    symbol: str
    line: int
    hit: _Hit


@dataclass(frozen=True)
class _CallEdge:
    caller: tuple[str, str]
    callee: tuple[str, str]
    line: int


@dataclass(frozen=True)
class _ExecEdge:
    caller: tuple[str, str]
    ref: _ScriptRef
    line: int


def _module_name(path: str) -> str:
    stem = path.removesuffix(".pyi").removesuffix(".py")
    if stem.startswith("src/"):
        stem = stem[4:]
    if stem.endswith("/__init__"):
        stem = stem[: -len("/__init__")]
    return stem.replace("/", ".")


def _param_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    args = node.args
    names = [a.arg for a in (*args.posonlyargs, *args.args)]
    if args.vararg is not None:
        names.append("*" + args.vararg.arg)
    names.extend(a.arg for a in args.kwonlyargs)
    return tuple(names)


class _Module:
    """One Python file: its imports, its functions and their environments."""

    def __init__(
        self,
        path: str,
        tree: ast.Module,
        index: dict[str, str],
        siblings: dict[str, dict[str, str]],
    ) -> None:
        self.path = path
        self.tree = tree
        self.name = _module_name(path)
        self.imports: dict[str, str] = {}
        self.functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.classes: set[str] = set()
        self.owner: dict[str, str] = {}
        self.decorators: set[int] = set()
        self.http_client = False
        self.aliases: dict[str, str] = {}
        self._index = index
        self._siblings = siblings
        self._collect(tree.body, prefix="", owner_class=None)
        self._collect_imports()
        roots = {v.split(".", 1)[0] for v in self.imports.values()}
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                name_node, value = stmt.targets[0], stmt.value
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                name_node, value = stmt.target, stmt.value
            else:
                continue
            if not isinstance(name_node, ast.Name):
                continue
            if isinstance(value, ast.Name) and value.id in self.functions:
                self.aliases[name_node.id] = value.id
            elif isinstance(value, (ast.Name, ast.Attribute)):
                dotted = self.dotted(value)
                if dotted is not None and dotted.split(".", 1)[0] in roots:
                    self.imports.setdefault(name_node.id, dotted)
        self.http_client = any(
            target == client or target.startswith(client + ".")
            for target in self.imports.values()
            for client in _HTTP_CLIENT_MODULES
        )

    def _collect(
        self, body: Sequence[ast.stmt], prefix: str, owner_class: str | None
    ) -> None:
        for stmt in body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = prefix + stmt.name
                self.functions[qual] = stmt
                if owner_class is not None:
                    self.owner[qual] = owner_class
                self._collect(stmt.body, qual + ".", None)
            elif isinstance(stmt, ast.ClassDef):
                qual = prefix + stmt.name
                self.classes.add(qual)
                self._collect(stmt.body, qual + ".", qual)
            elif isinstance(stmt, (ast.If, ast.Try, ast.With, ast.AsyncWith)):
                for block in _blocks(stmt):
                    self._collect(block, prefix, owner_class)

    def _resolve_import(self, dotted: str) -> str:
        head = dotted.split(".", 1)[0]
        if dotted in self._index or head in self._index:
            return dotted
        sibling = self._siblings.get(posixpath.dirname(self.path), {}).get(head)
        if sibling is not None:
            tail = dotted[len(head) :]
            return _module_name(sibling) + tail
        return dotted

    def _collect_imports(self) -> None:
        package = self.name.split(".")
        if not self.path.endswith("__init__.py"):
            package = package[:-1]
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.decorators.update(
                    id(d) for d in node.decorator_list if isinstance(d, ast.Call)
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    target = self._resolve_import(alias.name)
                    if alias.asname:
                        self.imports[alias.asname] = target
                    else:
                        head = alias.name.split(".", 1)[0]
                        self.imports.setdefault(head, self._resolve_import(head))
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base_parts = package[: len(package) - (node.level - 1)]
                    base = ".".join(
                        [*base_parts, node.module] if node.module else base_parts
                    )
                else:
                    base = self._resolve_import(node.module or "")
                for alias in node.names:
                    self.imports[alias.asname or alias.name] = f"{base}.{alias.name}"

    def dotted(self, expr: ast.expr) -> str | None:
        """The import-resolved dotted name of a Name/Attribute chain."""
        parts: list[str] = []
        node: ast.expr = expr
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if not isinstance(node, ast.Name):
            return None
        root = self.imports.get(node.id, node.id)
        return ".".join([root, *reversed(parts)])


def _blocks(stmt: ast.stmt) -> list[Sequence[ast.stmt]]:
    if isinstance(stmt, ast.If):
        return [stmt.body, stmt.orelse]
    if isinstance(stmt, ast.Try):
        return [
            stmt.body,
            *(h.body for h in stmt.handlers),
            stmt.orelse,
            stmt.finalbody,
        ]
    if isinstance(stmt, (ast.With, ast.AsyncWith)):
        return [stmt.body]
    return []


def _own_nodes(root: ast.AST) -> Iterator[ast.AST]:
    """Walk ``root`` without entering nested function or class bodies."""
    stack: list[ast.AST] = list(ast.iter_child_nodes(root))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.Lambda):
            continue
        stack.extend(ast.iter_child_nodes(node))


_Event = tuple[str, ast.AST | str | None]


def _events(statements: Sequence[ast.stmt]) -> dict[str, list[_Event]]:
    """Every assignment and mutation of each local name, in source order."""
    events: dict[str, list[_Event]] = {}

    def add(name: str, event: _Event) -> None:
        events.setdefault(name, []).append(event)

    for stmt in statements:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            if stmt.value is None:
                continue
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    add(target.id, ("assign", stmt.value))
                elif (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and isinstance(target.slice, ast.Constant)
                    and isinstance(target.slice.value, str)
                ):
                    add(target.value.id, ("key", target.slice.value))
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for element in target.elts:
                        if isinstance(element, ast.Name):
                            add(element.id, ("opaque", None))
        elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
            add(stmt.target.id, ("aug", stmt.value))
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                if isinstance(item.optional_vars, ast.Name):
                    add(item.optional_vars.id, ("assign", item.context_expr))
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            func = stmt.value.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                kind = {
                    "append": "append",
                    "extend": "extend",
                    "update": "keys",
                    "setdefault": "keys",
                }.get(func.attr)
                if kind is not None:
                    add(func.value.id, (kind, stmt.value))
    return events


class _LazyEnv(Mapping[str, _Val]):
    """A unit's local names, each evaluated on first use and then memoised.

    A name's value is the join of all its assignments (flow-insensitive), so
    a gate cannot be passed by reassigning a name after the sink.
    """

    def __init__(
        self,
        analyzer: _Analyzer,
        module: _Module,
        qual: str,
        preset: dict[str, _Val],
        events: dict[str, list[_Event]],
        depth: int,
    ) -> None:
        self.analyzer = analyzer
        self.module = module
        self.qual = qual
        self.depth = depth
        self._preset = preset
        self._events = events
        self._memo: dict[str, _Val] = {}
        self._busy: set[str] = set()

    def __contains__(self, name: object) -> bool:
        return name in self._preset or name in self._events

    def __getitem__(self, name: str) -> _Val:
        if name in self._memo:
            return self._memo[name]
        if name not in self:
            raise KeyError(name)
        current = self._preset.get(name, _EMPTY)
        if name in self._busy:
            return current
        self._busy.add(name)
        try:
            for event in self._events.get(name, ()):
                current = self.analyzer._apply(self, current, event)
        finally:
            self._busy.discard(name)
        self._memo[name] = current
        return current

    def __iter__(self) -> Iterator[str]:
        return iter({*self._preset, *self._events})

    def __len__(self) -> int:
        return len({*self._preset, *self._events})


class _Analyzer:
    """The repository-wide fixpoint over summaries, sites and graph edges."""

    def __init__(
        self,
        policy: ModelDirectModelCallPolicy,
        repo: str,
        modules: dict[str, _Module],
        index: dict[str, str],
    ) -> None:
        self.policy = policy
        self.repo = repo
        self.compiled = _compile(policy)
        self.modules: dict[str, _Module] = {}
        self.index = index
        self.summaries: dict[tuple[str, str], _Summary] = {}
        self._units: dict[tuple[str, str], tuple[_Module, ast.AST]] = {}
        self.sites: list[_Site] = []
        self.calls: list[_CallEdge] = []
        self.execs: list[_ExecEdge] = []
        self._module_env: dict[str, _LazyEnv] = {}
        self._event_cache: dict[int, dict[str, list[_Event]]] = {}
        self._node_cache: dict[int, list[ast.AST]] = {}
        self._statement_cache: dict[int, list[ast.stmt]] = {}
        self._decorators: set[int] = set()
        self._callers: dict[tuple[str, str], set[tuple[str, str]]] = {}
        self.add(modules)

    # -- resolution ---------------------------------------------------------

    def _repo_function(self, dotted: str) -> tuple[str, str] | None:
        parts = dotted.split(".")
        for cut in range(len(parts) - 1, 0, -1):
            path = self.index.get(".".join(parts[:cut]))
            if path is None:
                continue
            qual = ".".join(parts[cut:])
            if (path, qual) in self.summaries:
                return (path, qual)
            module = self.modules.get(path)
            if module is not None and qual in module.imports:
                return self._repo_function(module.imports[qual])
            return None
        return None

    def _resolve(
        self, module: _Module, func: ast.expr, current: str
    ) -> tuple[str, str | tuple[str, str]]:
        """('repo', (path, qual)) | ('ext', dotted) | ('method', attr) | ('none', '')."""
        if isinstance(func, ast.Name):
            if func.id in module.aliases and func.id not in module.functions:
                func = ast.Name(id=module.aliases[func.id])
            local = self._local_function(module, func.id, current)
            if local is not None:
                return ("repo", (module.path, local))
            if func.id in module.imports:
                dotted = module.imports[func.id]
                found = self._repo_function(dotted)
                return ("repo", found) if found else ("ext", dotted)
            return ("ext", func.id)
        if isinstance(func, ast.Attribute):
            base = func.value
            if isinstance(base, ast.Name) and base.id in {"self", "cls"}:
                owner = module.owner.get(current)
                if owner and f"{owner}.{func.attr}" in module.functions:
                    return ("repo", (module.path, f"{owner}.{func.attr}"))
                return ("method", func.attr)
            if isinstance(base, ast.Name) and base.id in module.classes:
                qual = f"{base.id}.{func.attr}"
                if qual in module.functions:
                    return ("repo", (module.path, qual))
            root: ast.expr = base
            while isinstance(root, ast.Attribute):
                root = root.value
            attr_dotted = module.dotted(func)
            if attr_dotted is not None and isinstance(root, ast.Name):
                if root.id in module.imports:
                    found = self._repo_function(attr_dotted)
                    return ("repo", found) if found else ("ext", attr_dotted)
            return ("method", func.attr)
        return ("none", "")

    @staticmethod
    def _local_function(module: _Module, name: str, current: str) -> str | None:
        scope = current.split(".") if current != _MODULE else []
        while True:
            qual = ".".join([*scope, name])
            if qual in module.functions:
                return qual
            if not scope:
                return None
            scope.pop()

    # -- evaluation ---------------------------------------------------------

    def _nodes(self, root: ast.AST) -> list[ast.AST]:
        cached = self._node_cache.get(id(root))
        if cached is None:
            cached = list(_own_nodes(root))
            self._node_cache[id(root)] = cached
        return cached

    def _statements(self, root: ast.AST) -> list[ast.stmt]:
        cached = self._statement_cache.get(id(root))
        if cached is None:
            cached = [n for n in self._nodes(root) if isinstance(n, ast.stmt)]
            cached.sort(key=lambda n: (n.lineno, n.col_offset))
            self._statement_cache[id(root)] = cached
        return cached

    def _env_for(
        self, module: _Module, qual: str, node: ast.AST, depth: int
    ) -> _LazyEnv:
        preset: dict[str, _Val] = {}
        if qual != _MODULE and isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            for name in _param_names(node):
                bare = name.lstrip("*")
                labels = _name_labels(self.compiled, bare)
                preset[bare] = _Val(labels=labels, params=frozenset({name}))
        events = self._event_cache.get(id(node))
        if events is None:
            events = _events(self._statements(node))
            self._event_cache[id(node)] = events
        return _LazyEnv(self, module, qual, preset, events, depth)

    def _apply(
        self,
        env: _LazyEnv,
        current: _Val,
        event: tuple[str, ast.AST | str | None],
    ) -> _Val:
        """One assignment or mutation of a name, in source order."""
        kind, payload = event
        module, qual, depth = env.module, env.qual, env.depth
        if kind == "assign" and isinstance(payload, ast.expr):
            return _join(current, self._eval(module, qual, payload, env, depth))
        if kind == "opaque":
            return _join(current, _OPAQUE)
        if kind == "aug" and isinstance(payload, ast.expr):
            added = self._eval(module, qual, payload, env, depth)
            return _join(current, _concat(current, added))
        if kind == "key" and isinstance(payload, str):
            return replace(current, keys=current.keys | {payload})
        if not isinstance(payload, ast.Call) or current is _EMPTY:
            return current
        args = [self._eval(module, qual, a, env, depth) for a in payload.args]
        if kind == "append" and args and current.seq is not None:
            return replace(current, seq=(*current.seq, args[0]))
        if kind == "extend" and args and current.seq is not None:
            tail = args[0].seq if args[0].seq is not None else (_flatten(args[0]),)
            return replace(current, seq=(*current.seq, *tail))
        if kind == "keys":
            keys = {k.arg for k in payload.keywords if k.arg}
            for arg in args:
                keys |= arg.keys
            first = payload.args[0] if payload.args else None
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                keys.add(first.value)
            return replace(current, keys=current.keys | frozenset(keys))
        return current

    def _module_globals(self, module: _Module) -> _LazyEnv:
        cached = self._module_env.get(module.path)
        if cached is None:
            cached = self._env_for(module, _MODULE, module.tree, depth=_SUMMARY_DEPTH)
            self._module_env[module.path] = cached
        return cached

    def _identifier_val(self, name: str) -> _Val:
        labels = _name_labels(self.compiled, name)
        return _Val(texts=frozenset({_UNKNOWN}), labels=labels) if labels else _OPAQUE

    def _env_key_val(self, key: _Val, default: _Val) -> _Val:
        labels: frozenset[str] = frozenset()
        for text in key.texts:
            labels |= _name_labels(self.compiled, text, env_key=True)
        base = _Val(texts=frozenset({_UNKNOWN}), labels=labels)
        return _join(base, default) if default is not _EMPTY else base

    def _eval(
        self,
        module: _Module,
        qual: str,
        expr: ast.expr,
        env: Mapping[str, _Val],
        depth: int,
    ) -> _Val:
        if isinstance(expr, ast.Constant):
            if isinstance(expr.value, str):
                return _Val(texts=frozenset({expr.value}))
            if isinstance(expr.value, bytes):
                return _Val(texts=frozenset({expr.value.decode("latin-1")}))
            return _Val(texts=frozenset({str(expr.value)}))
        if isinstance(expr, ast.Name):
            if expr.id in env:
                return env[expr.id]
            if qual != _MODULE:
                globals_env = self._module_globals(module)
                if expr.id in globals_env:
                    return globals_env[expr.id]
            if module.imports.get(expr.id) == "sys.executable":
                return _Val(texts=frozenset({_UNKNOWN}), labels=frozenset({"python"}))
            return self._identifier_val(expr.id)
        if isinstance(expr, ast.Attribute):
            if module.dotted(expr) == "sys.executable":
                return _Val(texts=frozenset({_UNKNOWN}), labels=frozenset({"python"}))
            return self._identifier_val(expr.attr)
        if isinstance(expr, ast.Subscript):
            return self._eval_subscript(module, qual, expr, env, depth)
        if isinstance(expr, ast.JoinedStr):
            pieces: list[_Val] = []
            for part in expr.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    pieces.append(_Val(texts=frozenset({part.value})))
                elif isinstance(part, ast.FormattedValue):
                    pieces.append(
                        _flatten(self._eval(module, qual, part.value, env, depth))
                    )
            return _concat(*pieces)
        if isinstance(expr, ast.BinOp):
            left = self._eval(module, qual, expr.left, env, depth)
            right = self._eval(module, qual, expr.right, env, depth)
            if isinstance(expr.op, ast.Add):
                if left.seq is not None and right.seq is not None:
                    return _Val(seq=(*left.seq, *right.seq))
                return _concat(_flatten(left), _flatten(right))
            if isinstance(expr.op, ast.Div):
                return _concat(left, _Val(texts=frozenset({"/"})), right)
            return _join(_flatten(left), _Val(labels=right.labels, params=right.params))
        if isinstance(expr, ast.BoolOp):
            return _join(
                *(self._eval(module, qual, v, env, depth) for v in expr.values)
            )
        if isinstance(expr, ast.IfExp):
            return _join(
                self._eval(module, qual, expr.body, env, depth),
                self._eval(module, qual, expr.orelse, env, depth),
            )
        if isinstance(expr, (ast.List, ast.Tuple)):
            elements: list[_Val] = []
            for element in expr.elts:
                if isinstance(element, ast.Starred):
                    inner = self._eval(module, qual, element.value, env, depth)
                    if inner.seq is not None:
                        elements.extend(inner.seq)
                    else:
                        elements.append(_flatten(inner))
                else:
                    elements.append(self._eval(module, qual, element, env, depth))
            return _Val(seq=tuple(elements))
        if isinstance(expr, ast.Dict):
            keys = frozenset(
                k.value
                for k in expr.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)
            )
            spread = [
                self._eval(module, qual, v, env, depth)
                for k, v in zip(expr.keys, expr.values, strict=True)
                if k is None
            ]
            return _Val(keys=keys | frozenset(x for s in spread for x in s.keys))
        if isinstance(expr, ast.Call):
            return self._eval_call(module, qual, expr, env, depth)
        if isinstance(expr, (ast.Await, ast.NamedExpr)):
            return self._eval(module, qual, expr.value, env, depth)
        return _EMPTY

    def _eval_subscript(
        self,
        module: _Module,
        qual: str,
        expr: ast.Subscript,
        env: Mapping[str, _Val],
        depth: int,
    ) -> _Val:
        key = self._eval(module, qual, expr.slice, env, depth)
        target = module.dotted(expr.value)
        if target in {"os.environ", "os.environb"}:
            return self._env_key_val(key, _EMPTY)
        base = self._eval(module, qual, expr.value, env, depth)
        if base.seq is not None and isinstance(expr.slice, ast.Constant):
            index = expr.slice.value
            if isinstance(index, int) and -len(base.seq) <= index < len(base.seq):
                return base.seq[index]
        labels = frozenset(
            lab for t in key.texts for lab in _name_labels(self.compiled, t)
        )
        return _Val(texts=frozenset({_UNKNOWN}), labels=labels, params=base.params)

    def _eval_call(
        self,
        module: _Module,
        qual: str,
        call: ast.Call,
        env: Mapping[str, _Val],
        depth: int,
    ) -> _Val:
        def arg(i: int) -> _Val:
            if i < len(call.args) and not isinstance(call.args[i], ast.Starred):
                return self._eval(module, qual, call.args[i], env, depth)
            return _EMPTY

        func = call.func
        dotted = (
            module.dotted(func) if isinstance(func, (ast.Name, ast.Attribute)) else None
        )
        if dotted in {"os.environ.get", "os.getenv", "os.environ.setdefault"}:
            return self._env_key_val(arg(0), arg(1))
        if dotted in {"os.path.join", "posixpath.join", "urllib.parse.urljoin"}:
            pieces: list[_Val] = []
            for index in range(len(call.args)):
                if index:
                    pieces.append(_Val(texts=frozenset({"/"})))
                pieces.append(_flatten(arg(index)))
            return _concat(*pieces)
        if dotted in {
            "shutil.which",
            "str",
            "list",
            "tuple",
            "pathlib.Path",
            "Path",
            "os.fspath",
        }:
            return arg(0)
        if dotted in {"json.dumps", "json.dump", "orjson.dumps"}:
            return arg(0)
        if dotted == "shlex.split":
            source = arg(0)
            texts = sorted(t for t in source.texts if _UNKNOWN not in t)
            if texts:
                try:
                    tokens = shlex.split(texts[0])
                except ValueError:
                    tokens = texts[0].split()
                return _Val(seq=tuple(_Val(texts=frozenset({t})) for t in tokens))
            return _Val(texts=source.texts, labels=source.labels, params=source.params)
        if dotted == "dict":
            keys = frozenset(k.arg for k in call.keywords if k.arg)
            spread = arg(0)
            return _Val(keys=keys | spread.keys)
        if dotted == "importlib.import_module":
            return _EMPTY
        if isinstance(func, ast.Attribute):
            receiver = self._eval(module, qual, func.value, env, depth)
            if func.attr == "join" and receiver.texts and call.args:
                items = arg(0)
                separator = sorted(receiver.texts)[0]
                if items.seq is not None:
                    pieces = []
                    for index, element in enumerate(items.seq):
                        if index:
                            pieces.append(_Val(texts=frozenset({separator})))
                        pieces.append(_flatten(element))
                    return _concat(*pieces)
                return _concat(_flatten(items))
            if func.attr in {
                "rstrip",
                "lstrip",
                "strip",
                "removesuffix",
                "removeprefix",
                "encode",
                "decode",
                "lower",
                "upper",
                "copy",
                "resolve",
                "absolute",
                "expanduser",
            }:
                return receiver
            if func.attr == "format":
                return _concat(_flatten(receiver))
            if func.attr == "joinpath":
                pieces = [receiver]
                for index in range(len(call.args)):
                    pieces.extend([_Val(texts=frozenset({"/"})), _flatten(arg(index))])
                return _concat(*pieces)
            if func.attr == "get" and call.args:
                labels = frozenset(
                    lab for t in arg(0).texts for lab in _name_labels(self.compiled, t)
                )
                if labels:
                    return _join(
                        _Val(texts=frozenset({_UNKNOWN}), labels=labels), arg(1)
                    )
        kind, ref = self._resolve(module, func, qual)
        if kind == "repo" and isinstance(ref, tuple) and depth > 0:
            summary = self.summaries.get(ref)
            if summary is not None:
                binding = self._bind_args(module, qual, call, summary, env, depth, func)
                return _substitute(summary.returns, binding)
        return _OPAQUE

    def _bind_args(
        self,
        module: _Module,
        qual: str,
        call: ast.Call,
        summary: _Summary,
        env: Mapping[str, _Val],
        depth: int,
        func: ast.expr,
    ) -> dict[str, _Val]:
        params = list(summary.params)
        if summary.is_method and isinstance(func, ast.Attribute) and params:
            params = params[1:]
        binding: dict[str, _Val] = {}
        positional = [p for p in params if not p.startswith("*")]
        for index, node in enumerate(call.args):
            if isinstance(node, ast.Starred):
                break
            if index < len(positional):
                binding[positional[index]] = self._eval(
                    module, qual, node, env, depth - 1
                )
        for keyword in call.keywords:
            if keyword.arg and keyword.arg in params:
                binding[keyword.arg] = self._eval(
                    module, qual, keyword.value, env, depth - 1
                )
        return binding

    # -- sinks --------------------------------------------------------------

    def _analyse(self, module: _Module, qual: str, node: ast.AST, record: bool) -> bool:
        """Evaluate one function (or the module body); return True if its summary changed."""
        env = (
            self._module_globals(module)
            if qual == _MODULE
            else self._env_for(module, qual, node, _SUMMARY_DEPTH)
        )
        summary = self.summaries.get((module.path, qual))
        returns: list[_Val] = []
        param_sinks: dict[str, set[str]] = {}
        for child in self._nodes(node):
            if isinstance(child, ast.Return) and child.value is not None and summary:
                returns.append(
                    self._eval(module, qual, child.value, env, _SUMMARY_DEPTH)
                )
            if isinstance(child, (ast.Import, ast.ImportFrom)) and record:
                self._sdk_import(module, qual, child)
            if isinstance(child, ast.Call) and id(child) not in self._decorators:
                self._call_sites(module, qual, child, env, param_sinks, record)
        if summary is None:
            return False
        new_returns = _join(*returns) if returns else _EMPTY
        new_sinks = {k: frozenset(v) for k, v in param_sinks.items()}
        changed = new_returns != summary.returns or new_sinks != summary.param_sinks
        summary.returns = new_returns
        summary.param_sinks = new_sinks
        return changed

    def _record(self, module: _Module, qual: str, line: int, hit: _Hit) -> None:
        self.sites.append(_Site(module.path, qual, line, hit))

    def _sdk_import(
        self, module: _Module, qual: str, node: ast.Import | ast.ImportFrom
    ) -> None:
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif node.level == 0 and node.module:
            names = [node.module]
        for name in names:
            for sdk in self.policy.model_sdk_modules:
                if name == sdk or name.startswith(sdk + "."):
                    self._record(
                        module,
                        qual,
                        node.lineno,
                        _Hit("sdk_import", sdk, f"imports the model SDK {name}"),
                    )
                    break

    def _call_sites(
        self,
        module: _Module,
        qual: str,
        call: ast.Call,
        env: Mapping[str, _Val],
        param_sinks: dict[str, set[str]],
        record: bool,
    ) -> None:
        def ev(node: ast.expr) -> _Val:
            return self._eval(module, qual, node, env, _SUMMARY_DEPTH)

        def positional(i: int) -> _Val:
            if i < len(call.args) and not isinstance(call.args[i], ast.Starred):
                return ev(call.args[i])
            return _EMPTY

        def keyword(*names: str) -> _Val:
            for kw in call.keywords:
                if kw.arg in names:
                    return ev(kw.value)
            return _EMPTY

        def sink(role: str, val: _Val, hits: list[_Hit]) -> None:
            if hits and record:
                for hit in hits:
                    self._record(module, qual, call.lineno, hit)
            if all(h.weak for h in hits) and val.params:
                for param in val.params:
                    param_sinks.setdefault(param, set()).add(role)

        kind, ref = self._resolve(module, call.func, qual)
        dotted = ref if kind == "ext" and isinstance(ref, str) else None

        if dotted == "importlib.import_module" and record:
            for text in positional(0).texts:
                for sdk in self.policy.model_sdk_modules:
                    if text == sdk or text.startswith(sdk + "."):
                        self._record(
                            module,
                            qual,
                            call.lineno,
                            _Hit("sdk_import", sdk, f"imports the model SDK {text}"),
                        )

        argv: _Val | None = None
        if dotted in _EXEC_FIRST_ARG:
            argv = positional(0) if call.args else keyword(*_EXEC_ARG_KEYWORDS)
        elif dotted in _EXEC_POSITIONAL:
            start = 1 if dotted in {"os.execl", "os.execlp", "os.execle"} else 0
            elements: list[_Val] = []
            for node in call.args[start:]:
                if isinstance(node, ast.Starred):
                    inner = ev(node.value)
                    elements.extend(
                        inner.seq if inner.seq is not None else (_flatten(inner),)
                    )
                else:
                    elements.append(ev(node))
            argv = _Val(seq=tuple(elements))
            if dotted != "asyncio.create_subprocess_exec" and call.args:
                program = ev(call.args[0])
                argv = _Val(seq=(program, *elements[1:])) if elements else argv
        elif dotted in _EXEC_SECOND_ARG:
            argv = positional(1)
            if argv.seq is not None and call.args:
                argv = _Val(seq=(positional(0), *argv.seq[1:]))
        elif dotted in _EXEC_THIRD_ARG:
            argv = positional(2)
        if argv is not None:
            refs: list[_ScriptRef] = []
            hits = _argv_hits(self.policy, argv, refs)
            if record:
                for script in refs:
                    self.execs.append(
                        _ExecEdge((module.path, qual), script, call.lineno)
                    )
            if not hits:
                if argv.seq is not None and argv.seq and argv.seq[0].params:
                    for param in argv.seq[0].params:
                        param_sinks.setdefault(param, set()).add("exec_program")
                elif argv.seq is None and argv.params:
                    for param in argv.params:
                        param_sinks.setdefault(param, set()).add("exec_argv")
            elif record:
                for hit in hits:
                    self._record(module, qual, call.lineno, hit)
            return

        method = ref if kind == "method" and isinstance(ref, str) else None
        if dotted in _HTTP_FUNCTIONS or method in _HTTP_METHODS:
            verb = (dotted or "").rsplit(".", 1)[-1] or (method or "")
            first, second = positional(0), positional(1)
            url = keyword("url")
            if url is _EMPTY:
                if (
                    verb in {"request", "stream", "ws_connect"}
                    and first.texts
                    and first.texts <= _HTTP_VERBS
                ):
                    url = second
                else:
                    url = first
            body = keyword(*_BODY_KEYWORDS)
            if body is _EMPTY and verb == "Request":
                body = second
            where = dotted or f".{method}()"
            if method in {"get", "send"}:
                # dict.get and queue.send are not HTTP: these are sends only in
                # a module that imports an HTTP client, and only with a URL that
                # is already a model URL.
                if module.http_client:
                    sink("http_url", _Val(), _url_hits(self.policy, url, where))
                return
            url_hits = _url_hits(self.policy, url, where)
            body_hits = _body_hits(self.policy, body, where)
            headers = keyword("headers")
            if "anthropic-version" in headers.keys:
                body_hits.append(
                    _Hit("http", "http", f"{where}: anthropic-version header")
                )
            sink("http_url", url, url_hits)
            if not url_hits:
                sink("http_body", body, body_hits)
            return

        if kind == "repo" and isinstance(ref, tuple):
            self._repo_call(module, qual, call, ref, env, param_sinks, record)

    def _repo_call(
        self,
        module: _Module,
        qual: str,
        call: ast.Call,
        callee: tuple[str, str],
        env: Mapping[str, _Val],
        param_sinks: dict[str, set[str]],
        record: bool,
    ) -> None:
        if record:
            self.calls.append(_CallEdge((module.path, qual), callee, call.lineno))
        summary = self.summaries.get(callee)
        if summary is None or not summary.param_sinks:
            return
        if is_sanctioned(self.policy, self.repo, callee[0]):
            return
        binding = self._bind_args(
            module, qual, call, summary, env, _SUMMARY_DEPTH + 1, call.func
        )
        name = callee[1]
        for param, roles in sorted(summary.param_sinks.items()):
            val = binding.get(param)
            if val is None:
                continue
            for role in sorted(roles):
                where = f"{name}({param})"
                refs: list[_ScriptRef] = []
                if role == "exec_program":
                    hits = _command_hits(self.policy, [val], refs)
                elif role == "exec_argv":
                    hits = _argv_hits(self.policy, val, refs)
                elif role == "http_url":
                    hits = _url_hits(self.policy, val, where)
                else:
                    hits = _body_hits(self.policy, val, where)
                if record:
                    for script in refs:
                        self.execs.append(
                            _ExecEdge((module.path, qual), script, call.lineno)
                        )
                if hits and record:
                    for hit in hits:
                        self._record(
                            module,
                            qual,
                            call.lineno,
                            replace(hit, evidence=f"{hit.evidence} (through {where})"),
                        )
                if all(h.weak for h in hits):
                    for own in val.params:
                        param_sinks.setdefault(own, set()).add(role)

    def add(self, modules: dict[str, _Module]) -> None:
        """Analyse ``modules`` on top of what is already analysed.

        Summaries reach a fixpoint over a worklist (a unit is re-analysed only
        when a function it calls changed its summary), then the new units are
        recorded. A module added later is a caller of what is already present,
        so earlier units are not revisited. Decorator calls (``@app.post("/route")``) register
        routes; they are not sends.
        """
        fresh = {p: m for p, m in modules.items() if p not in self.modules}
        self.modules.update(fresh)
        units: dict[tuple[str, str], tuple[_Module, ast.AST]] = {}
        for module in fresh.values():
            for qual, fn in module.functions.items():
                self.summaries[(module.path, qual)] = _Summary(
                    params=_param_names(fn), is_method=qual in module.owner
                )
            units[(module.path, _MODULE)] = (module, module.tree)
            for qual, fn in module.functions.items():
                units[(module.path, qual)] = (module, fn)
            self._decorators |= module.decorators
        for key, (module, node) in units.items():
            active = False
            for child in self._nodes(node):
                if isinstance(child, ast.Call):
                    active = True
                    kind, ref = self._resolve(module, child.func, key[1])
                    if kind == "repo" and isinstance(ref, tuple):
                        self._callers.setdefault(ref, set()).add(key)
                elif isinstance(child, (ast.Return, ast.Import, ast.ImportFrom)):
                    active = True
            if active:
                self._units[key] = (module, node)
        pending = sorted(k for k in units if k in self._units)
        for _ in range(_FIXPOINT_ROUNDS):
            if not pending:
                break
            following: set[tuple[str, str]] = set()
            for key in pending:
                module, node = self._units[key]
                if self._analyse(module, key[1], node, record=False):
                    following |= self._callers.get(key, set())
                    following.add((key[0], _MODULE))
                    self._module_env.pop(key[0], None)
            pending = sorted(k for k in following if k in self._units)
        self._module_env.clear()
        for key in sorted(units):
            if key in self._units:
                module, node = self._units[key]
                self._analyse(module, key[1], node, record=True)


# ---------------------------------------------------------------------------
# Shell analysis
# ---------------------------------------------------------------------------


def _shell_sites(
    policy: ModelDirectModelCallPolicy, path: str, text: str
) -> tuple[list[_Site], list[_ExecEdge]]:
    compiled = _compile(policy)
    sites: list[_Site] = []
    execs: list[_ExecEdge] = []
    labelled: dict[str, frozenset[str]] = {}

    def var_labels(names: Iterable[str]) -> frozenset[str]:
        labels: frozenset[str] = frozenset()
        for name in names:
            labels |= labelled.get(name, frozenset())
            labels |= _name_labels(compiled, name.lower(), env_key=False)
            labels |= _name_labels(compiled, name, env_key=True)
        if "base_url" in labels:
            return frozenset({"base_url"})
        return labels

    symbol = _SCRIPT
    logical: list[tuple[int, str]] = []
    pending = ""
    start = 0
    for number, raw in enumerate(text.splitlines(), start=1):
        if not pending:
            start = number
        if raw.rstrip().endswith("\\"):
            pending += raw.rstrip()[:-1] + " "
            continue
        logical.append((start, pending + raw))
        pending = ""
    if pending:
        logical.append((start, pending))
    state = _ShellState()
    for line_no, line in logical:
        stripped = line.strip()
        if state.heredoc is not None:
            if stripped == state.heredoc:
                state.heredoc = None
            continue
        if not stripped or stripped.startswith("#"):
            continue
        function = _SHELL_FUNCTION.match(line)
        if function:
            symbol = function.group(1)
            continue
        if stripped == "}" and symbol != _SCRIPT and not line.startswith((" ", "\t")):
            symbol = _SCRIPT
            continue
        assign = _SHELL_ASSIGN.match(line)
        if assign and " " not in assign.group(2).strip().strip("'\""):
            name = assign.group(1)
            labels = var_labels([name, *_SHELL_VAR.findall(assign.group(2))])
            if labels:
                labelled[name] = labels
        commands = _split_shell(line, state)
        nested: list[list[frozenset[str]]] = []
        for command in commands:
            for alternatives in command[1:]:
                token = min(alternatives)
                words = token.split()
                if len(words) > 1 and (
                    _NESTED_COMMAND.search(token)
                    or posixpath.basename(words[0])
                    in {*policy.model_clis, *policy.print_mode_clis, *policy.http_clis}
                ):
                    # A quoted command line handed to eval, a runner function or
                    # ssh: judge its commands too, ignoring bare words.
                    nested.extend(c for c in _split_shell(token) if len(c) > 1)
        for command in [*commands, *nested]:
            positions: list[_Val] = []
            for alternatives in command:
                token = next(iter(alternatives))
                labels = var_labels(_SHELL_VAR.findall(token))
                positions.append(_Val(texts=frozenset({token}), labels=labels))
            refs: list[_ScriptRef] = []
            for hit in _command_hits(policy, positions, refs):
                sites.append(_Site(path, symbol, line_no, hit))
            execs.extend(_ExecEdge((path, symbol), ref, line_no) for ref in refs)
    return sites, execs


# ---------------------------------------------------------------------------
# Repository scan
# ---------------------------------------------------------------------------


def _index(paths: Iterable[str]) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    index: dict[str, str] = {}
    siblings: dict[str, dict[str, str]] = {}
    for path in sorted(paths):
        if not path.endswith(_PYTHON_SUFFIXES):
            continue
        index.setdefault(_module_name(path), path)
        stem = posixpath.basename(path).removesuffix(".pyi").removesuffix(".py")
        siblings.setdefault(posixpath.dirname(path), {}).setdefault(stem, path)
    return index, siblings


def _script_matches(ref: _ScriptRef, path: str) -> bool:
    if ref.is_module:
        return _module_name(path) == ref.name or _module_name(path).endswith(
            "." + ref.name
        )
    name = ref.name.strip("'\"")
    if _UNKNOWN in name:
        tail = name.rsplit(_UNKNOWN, 1)[-1].lstrip("/")
        return bool(tail) and (path == tail or path.endswith("/" + tail))
    normal = posixpath.normpath(name).lstrip("./")
    return path == normal or path.endswith("/" + normal)


def _sink_hint(policy: ModelDirectModelCallPolicy) -> re.Pattern[str]:
    """Text a Python file must contain to hold a sink of its own."""
    words = [
        r"subprocess",
        r"os\.(?:system|popen|exec|spawn|posix_spawn)",
        r"create_subprocess",
        r"pexpect",
        r"sys\.executable",
        r"importlib",
        r"\.(?:post|put|patch|request|stream|ws_connect)\(",
        *(re.escape(m) for m in policy.http_client_modules),
        *(re.escape(m) for m in policy.model_sdk_modules),
    ]
    return re.compile("|".join(words))


def _propagate(
    sites: list[_Site],
    calls: Sequence[_CallEdge],
    execs: Sequence[_ExecEdge],
    sanctioned: set[str],
) -> tuple[list[_Site], set[tuple[str, str]]]:
    """call_via and exec_via sites, and every model-calling function, to a fixpoint."""
    calling: set[tuple[str, str]] = {(s.path, s.symbol) for s in sites}
    calling_files: set[str] = {s.path for s in sites}
    found: dict[tuple[str, str, str, str, int], _Site] = {}
    changed = True
    while changed:
        changed = False
        for edge in calls:
            if edge.callee not in calling or edge.caller[0] in sanctioned:
                continue
            if edge.caller[0] != edge.callee[0]:
                target = f"{edge.callee[0]}::{edge.callee[1]}"
                key = (*edge.caller, "call_via", target, edge.line)
                if key not in found:
                    found[key] = _Site(
                        edge.caller[0],
                        edge.caller[1],
                        edge.line,
                        _Hit("call_via", target, f"calls the model-calling {target}"),
                    )
            if edge.caller not in calling:
                calling.add(edge.caller)
                calling_files.add(edge.caller[0])
                changed = True
        for exec_edge in execs:
            if exec_edge.caller[0] in sanctioned:
                continue
            for path in sorted(calling_files):
                if path == exec_edge.caller[0] or not _script_matches(
                    exec_edge.ref, path
                ):
                    continue
                key = (*exec_edge.caller, "exec_via", path, exec_edge.line)
                if key not in found:
                    found[key] = _Site(
                        exec_edge.caller[0],
                        exec_edge.caller[1],
                        exec_edge.line,
                        _Hit(
                            "exec_via", path, f"executes the model-calling file {path}"
                        ),
                    )
                if exec_edge.caller not in calling:
                    calling.add(exec_edge.caller)
                    calling_files.add(exec_edge.caller[0])
                    changed = True
    return list(found.values()), calling


def _mentions(keys: Iterable[tuple[str, str]]) -> set[tuple[str, str]]:
    """(function name, module or package name) pairs a file must both name to
    call one of ``keys`` from another file."""
    pairs: set[tuple[str, str]] = set()
    for path, qual in keys:
        if qual in {_MODULE, _SCRIPT}:
            continue
        parts = _module_name(path).split(".")
        for part in parts[-2:]:
            pairs.add((qual.rsplit(".", 1)[-1], part))
    return pairs


_WORD: Final[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def scan(
    policy: ModelDirectModelCallPolicy, scan_input: ModelDirectModelCallScanInput
) -> tuple[ModelDirectModelCallFinding, ...]:
    """Every direct model call site of the repository outside its sanctioned packages.

    Demand-driven: a Python file is parsed when its text could hold a sink
    (an exec, an HTTP client, a ``.get(``/``.post(`` call, an SDK name), or when
    it names a function that calls a model or passes a parameter to a sink
    together with that function's module. The set grows until nothing new is
    named.

    Raises SyntaxError for a parsed Python file that does not parse: the gate
    fails closed rather than skip it.
    """
    repo = scan_input.repo
    files = {f.path: f for f in scan_input.files}
    python = {p for p in files if p.endswith(_PYTHON_SUFFIXES)}
    index, siblings = _index(python)
    sanctioned = {p for p in files if is_sanctioned(policy, repo, p)}

    shell_sites: list[_Site] = []
    shell_execs: list[_ExecEdge] = []
    for path, source in sorted(files.items()):
        if path.endswith(_SHELL_SUFFIXES) or _is_shell_script(source):
            found_sites, found_execs = _shell_sites(policy, path, source.content)
            shell_sites.extend(found_sites)
            shell_execs.extend(found_execs)

    parsed: dict[str, _Module] = {}

    def load(paths: Iterable[str]) -> None:
        for path in sorted(paths):
            if path not in parsed:
                tree = ast.parse(files[path].content, filename=path)
                parsed[path] = _Module(path, tree, index, siblings)

    hint = _sink_hint(policy)
    selected = {p for p in python if hint.search(files[p].content)}
    load(selected)
    word_sets: dict[str, frozenset[str]] = {}
    asked: set[tuple[str, str]] = set()

    analyzer = _Analyzer(policy, repo, {p: parsed[p] for p in selected}, index)
    while True:
        sites = [s for s in (*analyzer.sites, *shell_sites) if s.path not in sanctioned]
        strong = {s.path for s in sites if not s.hit.weak}
        sites = [s for s in sites if not s.hit.weak or s.path in strong]
        execs = [*analyzer.execs, *shell_execs]
        via, calling = _propagate(sites, analyzer.calls, execs, sanctioned)
        relevant = set(calling) | {
            key for key, summary in analyzer.summaries.items() if summary.param_sinks
        }
        pairs = _mentions(relevant) - asked
        asked |= pairs
        if not pairs:
            break
        new = set()
        for path in python - selected:
            words = word_sets.get(path)
            if words is None:
                words = frozenset(_WORD.findall(files[path].content))
                word_sets[path] = words
            if any(name in words and part in words for name, part in pairs):
                new.add(path)
        if not new:
            break
        load(new)
        selected |= new
        analyzer.add({p: parsed[p] for p in selected})

    unique: dict[tuple[str, str, int, str, str], _Site] = {}
    for site in (*sites, *via):
        unique.setdefault(
            (site.path, site.symbol, site.line, site.hit.kind, site.hit.target), site
        )
    findings = [
        ModelDirectModelCallFinding(
            path=s.path,
            line=s.line,
            kind=s.hit.kind,
            symbol=s.symbol,
            target=s.hit.target,
            evidence=s.hit.evidence,
        )
        for s in unique.values()
    ]
    findings.sort(key=lambda f: (f.path, f.line, f.kind, f.target))
    return tuple(findings)


def _is_shell_script(source: ModelDirectModelCallSourceFile) -> bool:
    if "." in posixpath.basename(source.path):
        return False
    first = source.content.split("\n", 1)[0]
    return first.startswith("#!") and any(
        shell in first for shell in ("/sh", "bash", "zsh", "env sh")
    )


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelDirectModelCallComparison:
    """The ratchet verdict: what is new, what is stale, what has expired."""

    new: tuple[ModelDirectModelCallFinding, ...]
    stale: tuple[ModelDirectModelCallBaselineEntry, ...]
    expired: tuple[ModelDirectModelCallBaselineEntry, ...]


def entry_problems(
    policy: ModelDirectModelCallPolicy,
    entries: Sequence[ModelDirectModelCallBaselineEntry],
) -> list[str]:
    """Entries that name the wrong removal ticket for their target."""
    problems: list[str] = []
    for entry in entries:
        required = policy.required_ticket_by_target.get(entry.target)
        if required is not None and entry.ticket != required:
            problems.append(
                f"{entry.path}: {entry.kind} {entry.target} in {entry.symbol} must name "
                f"{required} for its removal, not {entry.ticket}"
            )
    return problems


def compare_with_baseline(
    findings: Sequence[ModelDirectModelCallFinding],
    baseline: Sequence[ModelDirectModelCallBaselineEntry],
    today: date,
) -> ModelDirectModelCallComparison:
    """Match findings to baseline entries as a multiset keyed by site, not line."""
    live = Counter(e.key() for e in baseline if e.expires >= today)
    seen = Counter(f.key() for f in findings)
    new: list[ModelDirectModelCallFinding] = []
    used: Counter[tuple[str, str, str, str]] = Counter()
    for finding in findings:
        key = finding.key()
        if used[key] < live[key]:
            used[key] += 1
        else:
            new.append(finding)
    stale: list[ModelDirectModelCallBaselineEntry] = []
    budget = Counter(seen)
    for entry in sorted(baseline, key=lambda e: e.key()):
        if budget[entry.key()] > 0:
            budget[entry.key()] -= 1
        else:
            stale.append(entry)
    expired = [e for e in baseline if e.expires < today]
    return ModelDirectModelCallComparison(
        new=tuple(new), stale=tuple(stale), expired=tuple(expired)
    )


def added_entries(
    base: Sequence[ModelDirectModelCallBaselineEntry],
    head: Sequence[ModelDirectModelCallBaselineEntry],
) -> list[ModelDirectModelCallBaselineEntry]:
    """Entries of ``head`` that ``base`` did not carry, or carried with an
    earlier expiry or another ticket. Entries only leave; none is extended."""
    remaining = Counter((e.key(), e.ticket, e.expires) for e in base)
    grown: list[ModelDirectModelCallBaselineEntry] = []
    for entry in head:
        signature = (entry.key(), entry.ticket, entry.expires)
        if remaining[signature] > 0:
            remaining[signature] -= 1
        else:
            grown.append(entry)
    return grown


class HandlerDirectModelCallCompute:
    """COMPUTE handler: a repository's files in, its direct model call sites out."""

    def __init__(self, policy: ModelDirectModelCallPolicy) -> None:
        self._policy = policy

    @property
    def handler_id(self) -> str:
        return "handler_direct_model_call_compute"

    def handle(
        self, scan_input: ModelDirectModelCallScanInput
    ) -> tuple[ModelDirectModelCallFinding, ...]:
        return scan(self._policy, scan_input)
