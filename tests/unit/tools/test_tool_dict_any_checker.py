# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure-unit tests for the ``DictAnyCheckerPlugin`` mypy plugin.

The plugin detects unguarded ``dict[str, Any]`` usage in function signatures
and recognizes the ``@allow_dict_any`` escape-hatch decorator. These tests
exercise the plugin's detection primitives directly against hand-constructed
mypy AST / type objects (``NameExpr``, ``MemberExpr``, ``CallExpr``,
``Instance``, ``AnyType``, ``FuncDef``, ``Decorator``) so no ``mypy`` type-check
run — and therefore no infrastructure — is required.

Coverage focuses on:

* ``_is_dict_str_any`` — the core type predicate, including the edge cases
  called out in OMN-7902 (empty / bare dict, wrong key type, wrong arg count,
  ``dict[str, str]`` negatives, and ``typing.Dict`` aliasing).
* decorator-name extraction and matching
  (``_get_decorator_name`` / ``_get_expression_name`` /
  ``_is_allow_dict_any_decorator`` / ``_check_decorators``) across the
  bare-name, ``@module.name``, and ``@name(...)`` call forms.
* the definition-time helpers ``check_function_for_dict_any`` and
  ``check_decorator_has_allow_dict_any``.
* ``_has_allow_decorator`` on a ``Decorator`` node.
* ``report_config_data`` cache-clearing and the signature/method hook gating.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from mypy.nodes import (
    ARG_POS,
    Argument,
    Block,
    CallExpr,
    ClassDef,
    Decorator,
    Expression,
    FuncDef,
    IntExpr,
    MemberExpr,
    NameExpr,
    SymbolTable,
    TypeInfo,
    Var,
)
from mypy.options import Options
from mypy.types import AnyType, CallableType, Instance, Type, TypeOfAny

from omnibase_core.tools.mypy_plugins.tool_dict_any_checker import (
    DictAnyCheckerPlugin,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# Construction helpers for mypy AST / type objects
# --------------------------------------------------------------------------- #
def _make_type_info(fullname: str) -> TypeInfo:
    """Build a minimal ``TypeInfo`` for a fully-qualified class name."""
    module, _, name = fullname.rpartition(".")
    class_def = ClassDef(name, Block([]))
    class_def.fullname = fullname
    info = TypeInfo(SymbolTable(), class_def, module)
    info.mro = [info]
    return info


def _instance(fullname: str, args: list[Type] | None = None) -> Instance:
    return Instance(_make_type_info(fullname), args or [])


_STR = _instance("builtins.str")
_INT = _instance("builtins.int")
_ANY = AnyType(TypeOfAny.explicit)


def _dict(key: Type, value: Type) -> Instance:
    return _instance("builtins.dict", [key, value])


def _callable(
    ret: Type,
    arg_types: list[Type] | None = None,
    arg_names: list[str | None] | None = None,
) -> CallableType:
    arg_types = arg_types or []
    arg_names = arg_names or []
    return CallableType(
        arg_types,
        [ARG_POS] * len(arg_types),
        arg_names,
        ret,
        _instance("builtins.function"),
    )


def _funcdef(
    name: str,
    ret: Type,
    arg_types: list[Type] | None = None,
    arg_names: list[str | None] | None = None,
) -> FuncDef:
    arg_types = arg_types or []
    arg_names = arg_names or []
    args = [
        Argument(Var(n or ""), t, None, ARG_POS)
        for n, t in zip(arg_names, arg_types, strict=False)
    ]
    func_def = FuncDef(name, args, Block([]))
    callable_type = _callable(ret, arg_types, arg_names)
    callable_type.definition = func_def
    func_def.type = callable_type
    return func_def


def _name_expr(name: str, fullname: str | None = None) -> NameExpr:
    node = NameExpr(name)
    node.fullname = fullname  # type: ignore[assignment]
    return node


def _member_expr(
    base: Expression, name: str, fullname: str | None = None
) -> MemberExpr:
    node = MemberExpr(base, name)
    node.fullname = fullname  # type: ignore[assignment]
    return node


class _FakeApi:
    """Minimal stand-in for the mypy checker API used by the sig hooks.

    Only ``fail`` is exercised by the plugin's signature-checking path; the
    absence of a ``modules`` attribute drives ``_get_modules_from_context``
    down its "no modules available" branch (returning ``None``), which is the
    realistic state for these unit-level contexts.
    """

    def __init__(self) -> None:
        self.failures: list[tuple[str, object]] = []

    def fail(self, message: str, context: object) -> None:
        self.failures.append((message, context))


def _sig_ctx(signature: CallableType) -> SimpleNamespace:
    """Build a lightweight signature context (function or method shaped)."""
    return SimpleNamespace(
        api=_FakeApi(),
        context=object(),
        default_signature=signature,
    )


@pytest.fixture
def plugin() -> DictAnyCheckerPlugin:
    instance = DictAnyCheckerPlugin(Options())
    # ``_checked_functions`` is a class-level set shared across instances;
    # clear it so per-test state (signature-hook gating) is isolated.
    instance._checked_functions.clear()
    return instance


# The canonical fully-qualified name of the escape-hatch decorator.
_ALLOW_FULLNAME = "omnibase_core.decorators.decorator_allow_dict_any.allow_dict_any"


# --------------------------------------------------------------------------- #
# _is_dict_str_any — the core type predicate
# --------------------------------------------------------------------------- #
class TestIsDictStrAny:
    def test_dict_str_any_matches(self, plugin: DictAnyCheckerPlugin) -> None:
        assert plugin._is_dict_str_any(_dict(_STR, _ANY)) is True

    def test_typing_dict_alias_matches(self, plugin: DictAnyCheckerPlugin) -> None:
        assert plugin._is_dict_str_any(_instance("typing.Dict", [_STR, _ANY]))

    def test_dict_str_str_does_not_match(self, plugin: DictAnyCheckerPlugin) -> None:
        assert plugin._is_dict_str_any(_dict(_STR, _STR)) is False

    def test_dict_int_any_wrong_key_does_not_match(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        assert plugin._is_dict_str_any(_dict(_INT, _ANY)) is False

    def test_dict_non_instance_key_does_not_match(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        # key type is itself Any -> not an Instance -> no match
        assert plugin._is_dict_str_any(_dict(_ANY, _ANY)) is False

    def test_bare_dict_no_args_does_not_match(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        # empty/bare dict: zero type args -> len != 2 -> no match
        assert plugin._is_dict_str_any(_instance("builtins.dict", [])) is False

    def test_dict_single_arg_does_not_match(self, plugin: DictAnyCheckerPlugin) -> None:
        assert plugin._is_dict_str_any(_instance("builtins.dict", [_STR])) is False

    def test_non_dict_instance_does_not_match(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        assert plugin._is_dict_str_any(_instance("builtins.list", [_ANY])) is False

    def test_non_instance_type_does_not_match(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        assert plugin._is_dict_str_any(_ANY) is False

    def test_nested_dict_value_still_matches_outer(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        # dict[str, dict[str, str]] : value is a dict Instance, not Any.
        nested = _dict(_STR, _dict(_STR, _STR))
        assert plugin._is_dict_str_any(nested) is False


# --------------------------------------------------------------------------- #
# Decorator name extraction and matching
# --------------------------------------------------------------------------- #
class TestDecoratorNameExtraction:
    def test_name_expr_uses_fullname(self, plugin: DictAnyCheckerPlugin) -> None:
        node = _name_expr("allow_dict_any", _ALLOW_FULLNAME)
        assert plugin._get_decorator_name(node) == _ALLOW_FULLNAME

    def test_name_expr_without_fullname_uses_name(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        node = _name_expr("allow_dict_any", None)
        assert plugin._get_decorator_name(node) == "allow_dict_any"

    def test_call_expr_unwraps_to_callee(self, plugin: DictAnyCheckerPlugin) -> None:
        callee = _name_expr("allow_dict_any", _ALLOW_FULLNAME)
        call = CallExpr(callee, [], [], [])
        assert plugin._get_decorator_name(call) == _ALLOW_FULLNAME

    def test_member_expr_uses_fullname(self, plugin: DictAnyCheckerPlugin) -> None:
        base = _name_expr("mod", "mod")
        node = _member_expr(base, "allow_dict_any", _ALLOW_FULLNAME)
        assert plugin._get_decorator_name(node) == _ALLOW_FULLNAME

    def test_member_expr_without_fullname_builds_dotted_name(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        base = _name_expr("decorators", None)
        node = _member_expr(base, "allow_dict_any", None)
        assert plugin._get_decorator_name(node) == "decorators.allow_dict_any"

    def test_unknown_expression_returns_empty(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        assert plugin._get_decorator_name(IntExpr(5)) == ""

    def test_expression_name_nested_member(self, plugin: DictAnyCheckerPlugin) -> None:
        inner = _member_expr(_name_expr("a", None), "b", None)
        outer = _member_expr(inner, "c", None)
        # _get_decorator_name on outer with no fullname -> a.b.c
        assert plugin._get_decorator_name(outer) == "a.b.c"

    def test_expression_name_unknown_returns_empty(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        assert plugin._get_expression_name(IntExpr(1)) == ""


class TestIsAllowDictAnyDecorator:
    def test_exact_fullname(self, plugin: DictAnyCheckerPlugin) -> None:
        node = _name_expr("allow_dict_any", _ALLOW_FULLNAME)
        assert plugin._is_allow_dict_any_decorator(node) is True

    def test_short_name(self, plugin: DictAnyCheckerPlugin) -> None:
        node = _name_expr("allow_dict_any", None)
        assert plugin._is_allow_dict_any_decorator(node) is True

    def test_endswith_allow_dict_any(self, plugin: DictAnyCheckerPlugin) -> None:
        node = _name_expr("allow_dict_any", "some.aliased.path.allow_dict_any")
        assert plugin._is_allow_dict_any_decorator(node) is True

    def test_member_form(self, plugin: DictAnyCheckerPlugin) -> None:
        base = _name_expr("decorators", None)
        node = _member_expr(base, "allow_dict_any", None)
        assert plugin._is_allow_dict_any_decorator(node) is True

    def test_unrelated_decorator_is_false(self, plugin: DictAnyCheckerPlugin) -> None:
        node = _name_expr("staticmethod", "builtins.staticmethod")
        assert plugin._is_allow_dict_any_decorator(node) is False


class TestCheckDecorators:
    def test_empty_list_is_false(self, plugin: DictAnyCheckerPlugin) -> None:
        assert plugin._check_decorators([]) is False

    def test_single_match(self, plugin: DictAnyCheckerPlugin) -> None:
        allow = _name_expr("allow_dict_any", _ALLOW_FULLNAME)
        assert plugin._check_decorators([allow]) is True

    def test_stacked_decorator_match_anywhere(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        other = _name_expr("staticmethod", "builtins.staticmethod")
        allow = _name_expr("allow_dict_any", _ALLOW_FULLNAME)
        assert plugin._check_decorators([other, allow]) is True

    def test_no_match(self, plugin: DictAnyCheckerPlugin) -> None:
        other = _name_expr("staticmethod", "builtins.staticmethod")
        assert plugin._check_decorators([other]) is False


# --------------------------------------------------------------------------- #
# Definition-time helpers
# --------------------------------------------------------------------------- #
class TestCheckFunctionForDictAny:
    def test_return_type_flagged(self, plugin: DictAnyCheckerPlugin) -> None:
        func = _funcdef("get_data", _dict(_STR, _ANY))
        issues = plugin.check_function_for_dict_any(func)
        assert len(issues) == 1
        assert issues[0][0] == "return_type"
        assert "get_data" in issues[0][1]

    def test_parameter_flagged(self, plugin: DictAnyCheckerPlugin) -> None:
        func = _funcdef(
            "takes", _STR, arg_types=[_dict(_STR, _ANY)], arg_names=["payload"]
        )
        issues = plugin.check_function_for_dict_any(func)
        assert len(issues) == 1
        assert issues[0][0] == "parameter"
        assert "payload" in issues[0][1]

    def test_clean_signature_has_no_issues(self, plugin: DictAnyCheckerPlugin) -> None:
        func = _funcdef("ok", _STR, arg_types=[_STR], arg_names=["name"])
        assert plugin.check_function_for_dict_any(func) == []

    def test_decorated_function_is_skipped(self, plugin: DictAnyCheckerPlugin) -> None:
        func = _funcdef("serialize", _dict(_STR, _ANY))
        allow = _name_expr("allow_dict_any", _ALLOW_FULLNAME)
        decorator = Decorator(func, [allow], Var("serialize"))
        assert plugin.check_function_for_dict_any(decorator) == []

    def test_decorator_wrapping_without_allow_still_flags(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        func = _funcdef("serialize", _dict(_STR, _ANY))
        other = _name_expr("staticmethod", "builtins.staticmethod")
        decorator = Decorator(func, [other], Var("serialize"))
        issues = plugin.check_function_for_dict_any(decorator)
        assert issues and issues[0][0] == "return_type"

    def test_funcdef_without_type_returns_no_issues(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        func = FuncDef("bare", [], Block([]))
        func.type = None
        assert plugin.check_function_for_dict_any(func) == []

    def test_is_decorated_funcdef_is_conservative(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        func = _funcdef("wrapped", _dict(_STR, _ANY))
        func.is_decorated = True
        # Without a Decorator wrapper we cannot inspect decorators, so the
        # checker conservatively reports no issues.
        assert plugin.check_function_for_dict_any(func) == []


class TestCheckDecoratorHasAllowDictAny:
    def test_decorator_with_allow(self, plugin: DictAnyCheckerPlugin) -> None:
        func = _funcdef("serialize", _dict(_STR, _ANY))
        allow = _name_expr("allow_dict_any", _ALLOW_FULLNAME)
        decorator = Decorator(func, [allow], Var("serialize"))
        assert plugin.check_decorator_has_allow_dict_any(decorator) is True

    def test_decorator_without_allow(self, plugin: DictAnyCheckerPlugin) -> None:
        func = _funcdef("serialize", _dict(_STR, _ANY))
        other = _name_expr("staticmethod", "builtins.staticmethod")
        decorator = Decorator(func, [other], Var("serialize"))
        assert plugin.check_decorator_has_allow_dict_any(decorator) is False

    def test_undecorated_funcdef_returns_true(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        # Public helper returns "not is_decorated" for a bare FuncDef.
        func = _funcdef("plain", _STR)
        func.is_decorated = False
        assert plugin.check_decorator_has_allow_dict_any(func) is True


class TestHasAllowDecorator:
    def test_decorator_node_direct(self, plugin: DictAnyCheckerPlugin) -> None:
        func = _funcdef("serialize", _dict(_STR, _ANY))
        allow = _name_expr("allow_dict_any", _ALLOW_FULLNAME)
        decorator = Decorator(func, [allow], Var("serialize"))
        assert plugin._has_allow_decorator(decorator) is True

    def test_decorator_node_without_allow(self, plugin: DictAnyCheckerPlugin) -> None:
        func = _funcdef("serialize", _dict(_STR, _ANY))
        other = _name_expr("staticmethod", "builtins.staticmethod")
        decorator = Decorator(func, [other], Var("serialize"))
        assert plugin._has_allow_decorator(decorator) is False

    def test_funcdef_not_decorated_without_ctx(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        func = _funcdef("plain", _STR)
        func.is_decorated = False
        assert plugin._has_allow_decorator(func) is False


# --------------------------------------------------------------------------- #
# Signature-checking path (the live call-site hooks)
# --------------------------------------------------------------------------- #
class TestSignatureChecking:
    def test_function_signature_flags_return_type(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        func = _funcdef("get_data", _dict(_STR, _ANY))
        ctx = _sig_ctx(func.type)  # type: ignore[arg-type]
        returned = plugin._check_function_signature(ctx)  # type: ignore[arg-type]
        assert returned is func.type
        assert len(ctx.api.failures) == 1
        assert "returns dict[str, Any]" in ctx.api.failures[0][0]

    def test_method_signature_flags_parameter(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        func = _funcdef(
            "takes", _STR, arg_types=[_dict(_STR, _ANY)], arg_names=["payload"]
        )
        ctx = _sig_ctx(func.type)  # type: ignore[arg-type]
        plugin._check_method_signature(ctx)  # type: ignore[arg-type]
        assert len(ctx.api.failures) == 1
        assert "parameter 'payload'" in ctx.api.failures[0][0]

    def test_clean_signature_emits_no_failure(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        func = _funcdef("ok", _STR, arg_types=[_STR], arg_names=["name"])
        ctx = _sig_ctx(func.type)  # type: ignore[arg-type]
        plugin._check_function_signature(ctx)  # type: ignore[arg-type]
        assert ctx.api.failures == []

    def test_both_return_and_param_flagged(self, plugin: DictAnyCheckerPlugin) -> None:
        func = _funcdef(
            "both",
            _dict(_STR, _ANY),
            arg_types=[_dict(_STR, _ANY)],
            arg_names=["cfg"],
        )
        ctx = _sig_ctx(func.type)  # type: ignore[arg-type]
        plugin._check_function_signature(ctx)  # type: ignore[arg-type]
        assert len(ctx.api.failures) == 2

    def test_signature_without_definition_is_ignored(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        # No ``definition`` on the callable -> the checker returns early with
        # no failures emitted.
        callable_type = _callable(_dict(_STR, _ANY))
        ctx = _sig_ctx(callable_type)
        plugin._check_function_signature(ctx)  # type: ignore[arg-type]
        assert ctx.api.failures == []

    def test_already_checked_function_is_skipped(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        func = _funcdef("dup", _dict(_STR, _ANY))
        func._fullname = "pkg.dup"
        assert func.fullname == "pkg.dup"
        plugin._checked_functions.add("pkg.dup")
        ctx = _sig_ctx(func.type)  # type: ignore[arg-type]
        plugin._check_function_signature(ctx)  # type: ignore[arg-type]
        assert ctx.api.failures == []


# --------------------------------------------------------------------------- #
# Plugin-level plumbing: report_config_data + hook gating
# --------------------------------------------------------------------------- #
class TestPluginPlumbing:
    def test_report_config_data_clears_cache(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        plugin._checked_functions.add("some.func")
        result = plugin.report_config_data(None)  # type: ignore[arg-type]
        assert result["plugin"] == "DictAnyCheckerPlugin"
        assert result["allow_decorator"] == plugin.ALLOW_DECORATOR
        assert plugin._checked_functions == set()

    def test_get_function_hook_returns_none(self, plugin: DictAnyCheckerPlugin) -> None:
        # Typed ``-> None``; asserting the sentinel triggers mypy's
        # func-returns-value, which is exactly the contract under test.
        assert (
            plugin.get_function_hook("anything")  # type: ignore[func-returns-value]
            is None
        )

    def test_get_method_hook_returns_none(self, plugin: DictAnyCheckerPlugin) -> None:
        assert (
            plugin.get_method_hook("anything")  # type: ignore[func-returns-value]
            is None
        )

    def test_function_signature_hook_returns_callback_when_unseen(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        assert callable(plugin.get_function_signature_hook("pkg.fresh_fn"))

    def test_function_signature_hook_none_when_already_seen(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        plugin._checked_functions.add("pkg.seen_fn")
        assert plugin.get_function_signature_hook("pkg.seen_fn") is None

    def test_method_signature_hook_returns_callback_when_unseen(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        assert callable(plugin.get_method_signature_hook("pkg.Cls.method"))

    def test_method_signature_hook_none_when_already_seen(
        self, plugin: DictAnyCheckerPlugin
    ) -> None:
        plugin._checked_functions.add("pkg.Cls.seen")
        assert plugin.get_method_signature_hook("pkg.Cls.seen") is None
