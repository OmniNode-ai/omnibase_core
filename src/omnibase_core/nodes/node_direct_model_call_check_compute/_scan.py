# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Shell analysis, the call-graph propagation and the repository scan (OMN-20295)."""

from __future__ import annotations

import ast
import posixpath
import re
from collections.abc import Iterable, Sequence

from omnibase_core.enums.enum_direct_model_call_kind import EnumDirectModelCallKind
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_finding import (
    ModelDirectModelCallFinding,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_policy import (
    ModelDirectModelCallPolicy,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_scan_input import (
    ModelDirectModelCallScanInput,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_source_file import (
    ModelDirectModelCallSourceFile,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._analyzer import _Analyzer
from omnibase_core.nodes.node_direct_model_call_check_compute._call_edge import (
    _CallEdge,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._commands import (
    _command_hits,
    _split_shell,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._constants import (
    _MODULE,
    _NESTED_COMMAND,
    _PYTHON_SUFFIXES,
    _SCRIPT,
    _SHELL_ASSIGN,
    _SHELL_FUNCTION,
    _SHELL_SUFFIXES,
    _SHELL_VAR,
    _UNKNOWN,
    _WORD,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._exec_edge import (
    _ExecEdge,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._hit import _Hit
from omnibase_core.nodes.node_direct_model_call_check_compute._module import (
    _Module,
    _module_name,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._policy_patterns import (
    _compile,
    _name_labels,
    is_sanctioned,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._script_ref import (
    _ScriptRef,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._shell_state import (
    _ShellState,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._site import _Site
from omnibase_core.nodes.node_direct_model_call_check_compute._value import _Val


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
                key = (
                    *edge.caller,
                    EnumDirectModelCallKind.CALL_VIA,
                    target,
                    edge.line,
                )
                if key not in found:
                    found[key] = _Site(
                        edge.caller[0],
                        edge.caller[1],
                        edge.line,
                        _Hit(
                            EnumDirectModelCallKind.CALL_VIA,
                            target,
                            f"calls the model-calling {target}",
                        ),
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
                key = (
                    *exec_edge.caller,
                    EnumDirectModelCallKind.EXEC_VIA,
                    path,
                    exec_edge.line,
                )
                if key not in found:
                    found[key] = _Site(
                        exec_edge.caller[0],
                        exec_edge.caller[1],
                        exec_edge.line,
                        _Hit(
                            EnumDirectModelCallKind.EXEC_VIA,
                            path,
                            f"executes the model-calling file {path}",
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
