# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import hashlib
import re

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

from omnibase_core.types.typed_dict_symbol_metadata import SymbolKind, SymbolTable

_PY_LANGUAGE = Language(tspython.language())
_PARSER = Parser(_PY_LANGUAGE)

_WHITESPACE = re.compile(r"\s+")


def _collapse_whitespace(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def _body_hash(body_source: str) -> str:
    return hashlib.sha256(body_source.encode()).hexdigest()


def _extract_signature_and_body(node: Node, source_lines: list[str]) -> tuple[str, str]:
    block_nodes = [c for c in node.children if c.type == "block"]
    if not block_nodes:
        sig_line = source_lines[node.start_point[0]]
        return _collapse_whitespace(sig_line.rstrip("\n")), ""

    block = block_nodes[0]
    sig_line = source_lines[node.start_point[0]]
    body_start = block.start_point[0]
    body_end = node.end_point[0]

    if body_start == node.start_point[0]:
        colon_index = sig_line.find(":", node.start_point[1])
        if colon_index >= 0:
            signature_source = sig_line[: colon_index + 1]
            body_source = sig_line[colon_index + 1 :]
        else:
            signature_source = sig_line[: block.start_point[1]]
            body_source = sig_line[block.start_point[1] :]
    else:
        signature_source = sig_line.rstrip("\n")
        body_source = "".join(source_lines[body_start : body_end + 1])

    signature = _collapse_whitespace(signature_source.rstrip("\n"))
    return signature, body_source


def _node_text(node: Node) -> str:
    return node.text.decode() if node.text else ""


def _definition_node(node: Node) -> Node:
    if node.type != "decorated_definition":
        return node

    for child in node.children:
        if child.type in {"class_definition", "function_definition"}:
            return child
    return node


def _process_function(
    node: Node,
    source_lines: list[str],
    result: SymbolTable,
    class_name: str | None = None,
) -> None:
    name_nodes = [c for c in node.children if c.type == "identifier"]
    if not name_nodes:
        return
    func_name = _node_text(name_nodes[0])
    full_name = f"{class_name}.{func_name}" if class_name else func_name

    signature, body_source = _extract_signature_and_body(node, source_lines)
    kind: SymbolKind = "method" if class_name else "function"

    result[full_name] = {
        "kind": kind,
        "signature": signature,
        "body_hash": _body_hash(body_source),
        "start_line": node.start_point[0] + 1,
        "end_line": node.end_point[0] + 1,
    }


def _process_class(
    node: Node,
    source_lines: list[str],
    result: SymbolTable,
) -> None:
    name_nodes = [c for c in node.children if c.type == "identifier"]
    if not name_nodes:
        return
    class_name = _node_text(name_nodes[0])

    signature, body_source = _extract_signature_and_body(node, source_lines)

    result[class_name] = {
        "kind": "class",
        "signature": signature,
        "body_hash": _body_hash(body_source),
        "start_line": node.start_point[0] + 1,
        "end_line": node.end_point[0] + 1,
    }

    block_nodes = [c for c in node.children if c.type == "block"]
    if not block_nodes:
        return
    block = block_nodes[0]
    for child in block.children:
        definition = _definition_node(child)
        if definition.type == "function_definition":
            _process_function(definition, source_lines, result, class_name=class_name)


def extract_symbols(content: str) -> SymbolTable:
    """Parse Python source and return per-symbol metadata for all top-level functions, classes, and their methods."""
    if not content.strip():
        return {}

    source_bytes = content.encode()
    tree = _PARSER.parse(source_bytes)
    root = tree.root_node
    source_lines = content.splitlines(keepends=True)

    result: SymbolTable = {}
    for node in root.children:
        definition = _definition_node(node)
        if definition.type == "function_definition":
            _process_function(definition, source_lines, result)
        elif definition.type == "class_definition":
            _process_class(definition, source_lines, result)

    return result
