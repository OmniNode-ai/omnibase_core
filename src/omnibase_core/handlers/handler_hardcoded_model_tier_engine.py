# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Families T and N of the hardcoded model-configuration scanner (OMN-21463, K6).

Pure and deterministic: it reads the text and the policy it is handed and does no
filesystem, network, environment or clock I/O. The names it judges are the
policy's ``tier_aliases``, ``tier_keys`` and ``engine_names``; this module spells
none of them.

* ``T``: a model tier alias as the value of a policy-shaped key, inside a
  ``Literal[...]``, or inside a tuple, list or set whose every member is a name of
  the engine ladder.
* ``N``: an engine name of the engine ladder as the value of a policy-shaped key,
  an enum (class-body) member, a ``Literal[...]`` member or an alias-dict key; a
  tier alias used as an alias-dict key is ``N`` too.

Python is judged on its syntax tree, so a docstring is prose and a comment is not
there at all. Other text forms (YAML, JSON, TOML, shell) are judged line by line on
text with comments already removed by the caller. A name that merely sits in a
list of other things (a CLI list, a handle-fragment list) is not judged.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from collections.abc import Set as AbstractSet
from functools import lru_cache
from typing import Final

from omnibase_core.validation.hardcoded_model_config.models import (
    LiteralFamily,
    ModelHardcodedModelConfigPolicy,
)

__all__ = ["scan_tier_engine"]

Hit = tuple[int, LiteralFamily, str]

_FLOW_SEQUENCE: Final[re.Pattern[str]] = re.compile(r"\[([^\[\]]*)\]")
_PYTHON_QUOTE: Final[str] = r"[rbuRBU]?[\"']"
_TEXT_QUOTE: Final[str] = r"[\"']?"


def _alternation(names: Iterable[str]) -> str:
    """Longest-first regex alternation of exact names (empty when there are none)."""
    return "|".join(
        re.escape(n) for n in sorted(set(names), key=lambda n: (-len(n), n))
    )


@lru_cache(maxsize=8)
def _patterns(
    policy: ModelHardcodedModelConfigPolicy,
) -> dict[str, re.Pattern[str] | None]:
    """Compile the line patterns. A pattern is ``None`` when its vocabulary is empty."""
    tiers = _alternation(policy.tier_aliases)
    keys = _alternation(policy.tier_keys)
    engines = _alternation(policy.engine_names)
    key_head = (
        r"(?<![A-Za-z0-9\-])[\"']?(?:" + keys + r")[\"']?"
        r"\s*(?::\s*[\w\[\], |.]+?\s*)?[:=]\s*"
    )

    def keyed(vocab: str, quote: str) -> re.Pattern[str] | None:
        if not (vocab and keys):
            return None
        return re.compile(
            key_head + quote + r"(?P<hit>" + vocab + r")[\"']?(?![\w.\-])",
            re.IGNORECASE,
        )

    def item(vocab: str) -> re.Pattern[str] | None:
        if not vocab:
            return None
        return re.compile(
            r"^\s*-\s+[\"']?(?P<hit>" + vocab + r")[\"']?\s*$", re.IGNORECASE
        )

    parent = (
        re.compile(r"^\s*[\"']?(?:" + keys + r")[\"']?\s*:\s*$", re.IGNORECASE)
        if keys
        else None
    )
    return {
        "tier_value_python": keyed(tiers, _PYTHON_QUOTE),
        "tier_value_text": keyed(tiers, _TEXT_QUOTE),
        "engine_value_python": keyed(engines, _PYTHON_QUOTE),
        "engine_value_text": keyed(engines, _TEXT_QUOTE),
        "tier_item": item(tiers),
        "engine_item": item(engines),
        "policy_key_line": parent,
    }


def _is_literal_subscript(node: ast.Subscript) -> bool:
    target = node.value
    return (isinstance(target, ast.Name) and target.id == "Literal") or (
        isinstance(target, ast.Attribute) and target.attr == "Literal"
    )


def _str_value(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.strip()
    return None


def _target_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_policy_key(name: str, keys: frozenset[str]) -> bool:
    lower = name.lower()
    return lower in keys or any(lower.endswith("_" + key) for key in keys)


def _classify_members(
    members: Iterable[str | None],
    tiers: frozenset[str],
    engines: frozenset[str],
) -> set[LiteralFamily]:
    """Families of a collection whose every member is a ladder name, else none.

    A set of tiers and engines is the ladder written out. A collection that
    carries any other member is a vocabulary of something else (a handle
    fragment list, a CLI list) and is not judged.
    """
    values = list(members)
    if not values or any(v is None or v not in tiers | engines for v in values):
        return set()
    found: set[LiteralFamily] = set()
    if any(v in tiers for v in values):
        found.add("T")
    if any(v in engines for v in values):
        found.add("N")
    return found


def _python_hits(
    text: str, policy: ModelHardcodedModelConfigPolicy, families: AbstractSet[str]
) -> list[Hit] | None:
    """Families T and N over the Python syntax tree, or None when it does not parse."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    tiers = frozenset(policy.tier_aliases)
    engines = frozenset(policy.engine_names)
    keys = frozenset(k.lower() for k in policy.tier_keys)
    hits: list[Hit] = []

    def add(node: ast.AST, family: LiteralFamily, value: str) -> None:
        if family in families:
            hits.append((getattr(node, "lineno", 1), family, value))

    def judge_name(node: ast.AST, value: str | None) -> None:
        if value in tiers:
            add(node, "T", value)
        elif value in engines and value is not None:
            add(node, "N", value)

    def judge_pair(name: str | None, value: ast.AST | None) -> None:
        if name is not None and _is_policy_key(name, keys) and value is not None:
            judge_name(value, _str_value(value))

    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple | ast.List | ast.Set):
            names = [_str_value(m) for m in node.elts]
            for family in _classify_members(names, tiers, engines):
                add(node, family, next(v for v in names if v))
        elif isinstance(node, ast.Subscript) and _is_literal_subscript(node):
            slice_ = node.slice
            for member in slice_.elts if isinstance(slice_, ast.Tuple) else [slice_]:
                judge_name(member, _str_value(member))
        elif isinstance(node, ast.Dict):
            for key, item in zip(node.keys, node.values, strict=True):
                key_text = _str_value(key)
                if key is not None and key_text in tiers | engines:
                    add(key, "N", key_text or "")
                else:
                    judge_pair(key_text, item)
        elif isinstance(node, ast.ClassDef):
            for statement in node.body:
                if isinstance(statement, ast.Assign | ast.AnnAssign):
                    member_value = _str_value(statement.value)
                    if member_value in engines and member_value is not None:
                        add(statement, "N", member_value)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                judge_pair(_target_name(target), node.value)
        elif isinstance(node, ast.AnnAssign):
            judge_pair(_target_name(node.target), node.value)
        elif isinstance(node, ast.keyword):
            judge_pair(node.arg, node.value)
    return hits


def _parent_is_policy_key(
    code: dict[int, str], n: int, pattern: re.Pattern[str] | None
) -> bool:
    """Whether the block list holding line ``n`` hangs from a policy-shaped key."""
    if pattern is None:
        return False
    indent = len(code[n]) - len(code[n].lstrip())
    for m in range(n - 1, 0, -1):
        above = code.get(m, "")
        if not above.strip():
            continue
        above_indent = len(above) - len(above.lstrip())
        if above_indent < indent or (
            above_indent == indent and not above.lstrip().startswith("-")
        ):
            return bool(pattern.match(above))
    return False


def _line_hits(
    n: int,
    code: dict[int, str],
    is_python: bool,
    families: AbstractSet[str],
    policy: ModelHardcodedModelConfigPolicy,
    structural: bool,
) -> list[Hit]:
    """Families T and N on one comment-stripped line.

    A policy-shaped key with a tier alias or engine name is judged in every text
    form. When the Python syntax tree already judged the file (``structural``),
    nothing else is; otherwise a flow sequence of ladder names and a block list
    item are.
    """
    patterns = _patterns(policy)
    suffix = "python" if is_python else "text"
    line = code.get(n, "")
    hits: list[Hit] = []
    pairs: tuple[tuple[LiteralFamily, re.Pattern[str] | None], ...] = (
        ("T", patterns["tier_value_" + suffix]),
        ("N", patterns["engine_value_" + suffix]),
    )
    for family, pattern in pairs:
        found = pattern.search(line) if pattern is not None else None
        if found and family in families:
            hits.append((n, family, found.group("hit")))
    if structural:
        return hits
    tiers = frozenset(policy.tier_aliases)
    engines = frozenset(policy.engine_names)
    for flow in _FLOW_SEQUENCE.finditer(line):
        members = [
            m.strip().strip("\"'") for m in flow.group(1).split(",") if m.strip()
        ]
        for family in _classify_members(members, tiers, engines):
            if family in families:
                hits.append((n, family, members[0]))
    tier_item, engine_item = patterns["tier_item"], patterns["engine_item"]
    if "T" in families and tier_item is not None and (found := tier_item.match(line)):
        hits.append((n, "T", found.group("hit")))
    if (
        "N" in families
        and engine_item is not None
        and (found := engine_item.match(line))
        and _parent_is_policy_key(code, n, patterns["policy_key_line"])
    ):
        hits.append((n, "N", found.group("hit")))
    return hits


def scan_tier_engine(
    text: str,
    code: dict[int, str],
    is_python: bool,
    policy: ModelHardcodedModelConfigPolicy,
    families: AbstractSet[str],
) -> list[Hit]:
    """Return ``(line, family, matched text)`` for families T and N in ``families``.

    ``code`` maps a 1-based line number to that line with comments (and, in
    Python, docstrings) blanked.
    """
    families = families & {"T", "N"}
    tree_hits = _python_hits(text, policy, families) if is_python else None
    hits: list[Hit] = list(tree_hits or [])
    for n in code:
        hits.extend(
            _line_hits(n, code, is_python, families, policy, tree_hits is not None)
        )
    return hits
