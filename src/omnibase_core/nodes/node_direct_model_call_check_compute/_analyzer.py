# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The repository-wide fixpoint over summaries, sites and graph edges (OMN-20295)."""

from __future__ import annotations

import ast
import shlex
from collections.abc import Mapping
from dataclasses import replace

from omnibase_core.enums.enum_direct_model_call_kind import EnumDirectModelCallKind
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_policy import (
    ModelDirectModelCallPolicy,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._call_edge import (
    _CallEdge,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._commands import (
    _argv_hits,
    _body_hits,
    _command_hits,
    _url_hits,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._constants import (
    _BODY_KEYWORDS,
    _EXEC_ARG_KEYWORDS,
    _EXEC_FIRST_ARG,
    _EXEC_POSITIONAL,
    _EXEC_SECOND_ARG,
    _EXEC_THIRD_ARG,
    _FIXPOINT_ROUNDS,
    _HTTP_FUNCTIONS,
    _HTTP_METHODS,
    _HTTP_VERBS,
    _MODULE,
    _SUMMARY_DEPTH,
    _UNKNOWN,
    _Event,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._exec_edge import (
    _ExecEdge,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._hit import _Hit
from omnibase_core.nodes.node_direct_model_call_check_compute._lazy_env import _LazyEnv
from omnibase_core.nodes.node_direct_model_call_check_compute._module import (
    _events,
    _Module,
    _own_nodes,
    _param_names,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._policy_patterns import (
    _compile,
    _name_labels,
    is_sanctioned,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._script_ref import (
    _ScriptRef,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._site import _Site
from omnibase_core.nodes.node_direct_model_call_check_compute._summary import _Summary
from omnibase_core.nodes.node_direct_model_call_check_compute._value import (
    _EMPTY,
    _OPAQUE,
    _concat,
    _flatten,
    _join,
    _substitute,
    _Val,
)


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
        return _LazyEnv(self._apply, module, qual, preset, events, depth)

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
                        _Hit(
                            EnumDirectModelCallKind.SDK_IMPORT,
                            sdk,
                            f"imports the model SDK {name}",
                        ),
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
                            _Hit(
                                EnumDirectModelCallKind.SDK_IMPORT,
                                sdk,
                                f"imports the model SDK {text}",
                            ),
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
                    _Hit(
                        EnumDirectModelCallKind.HTTP,
                        "http",
                        f"{where}: anthropic-version header",
                    )
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
