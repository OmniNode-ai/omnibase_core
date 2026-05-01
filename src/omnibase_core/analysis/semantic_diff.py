# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import re
from difflib import SequenceMatcher
from typing import cast

from omnibase_core.analysis.symbol_extractor import extract_symbols
from omnibase_core.enums.enum_diff_severity import EnumChangeKind, EnumDiffSeverity
from omnibase_core.models.analysis.model_semantic_diff_report import (
    ModelSemanticDiffReport,
)
from omnibase_core.models.analysis.model_symbol_change import ModelSymbolChange
from omnibase_core.types.typed_dict_extracted_symbol import TypedDictExtractedSymbol

_GUARD_PATTERN = re.compile(
    r"(?i)(guard|check|validate|verify|ensure|assert|require)",
)

_KIND_SEVERITY: dict[EnumChangeKind, EnumDiffSeverity] = {
    EnumChangeKind.GUARD_REMOVED: EnumDiffSeverity.CRITICAL,
    EnumChangeKind.SIGNATURE_CHANGE: EnumDiffSeverity.HIGH,
    EnumChangeKind.API_CHANGE: EnumDiffSeverity.HIGH,
    EnumChangeKind.DELETED_FUNCTION: EnumDiffSeverity.HIGH,
    EnumChangeKind.LOGIC_CHANGE: EnumDiffSeverity.MEDIUM,
    EnumChangeKind.REFACTOR: EnumDiffSeverity.MEDIUM,
    EnumChangeKind.NEW_FUNCTION: EnumDiffSeverity.LOW,
    EnumChangeKind.COSMETIC: EnumDiffSeverity.LOW,
}


def _line_count(sym: TypedDictExtractedSymbol) -> int:
    return sym["end_line"] - sym["start_line"] + 1


def _is_guard(name: str) -> bool:
    return bool(_GUARD_PATTERN.search(name))


def _strip_name(signature: str, name: str) -> str:
    """Replace the first occurrence of the symbol name in the signature."""
    return signature.replace(name, "__sym__", 1)


def _rename_tolerance(
    old_sym: TypedDictExtractedSymbol, new_sym: TypedDictExtractedSymbol
) -> bool:
    """True when a delete/add pair is similar enough to classify as a refactor."""
    old_name = old_sym.get("name", "")
    new_name = new_sym.get("name", "")
    old_sig = _strip_name(old_sym["signature"], old_name)
    new_sig = _strip_name(new_sym["signature"], new_name)
    if old_sig != new_sig:
        return False
    if old_sym["kind"] != new_sym["kind"]:
        return False
    if SequenceMatcher(None, old_name, new_name).ratio() < 0.6:
        return False
    old_lines = _line_count(old_sym)
    new_lines = _line_count(new_sym)
    max_lines = max(old_lines, new_lines)
    if max_lines == 0:
        return True
    return abs(old_lines - new_lines) / max_lines <= 0.20


def _symbol_with_name(
    sym: TypedDictExtractedSymbol, name: str
) -> TypedDictExtractedSymbol:
    return {
        "kind": sym["kind"],
        "signature": sym["signature"],
        "body_hash": sym["body_hash"],
        "start_line": sym["start_line"],
        "end_line": sym["end_line"],
        "name": name,
    }


def _make_change(
    kind: EnumChangeKind,
    name: str,
    file_path: str,
    consumers_count: int,
) -> ModelSymbolChange:
    return ModelSymbolChange(
        kind=kind,
        severity=_KIND_SEVERITY[kind],
        symbol_name=name,
        file_path=file_path,
        consumers_count=consumers_count,
    )


def compute_diff(
    old_source: str,
    new_source: str,
    file_path: str,
    consumers_count: int,
) -> ModelSemanticDiffReport:
    """Return a symbol-level semantic diff report for two Python source snapshots.

    Raises:
        ValueError: If ``consumers_count`` is negative.
    """
    if consumers_count < 0:
        raise ValueError(  # error-ok: public API intentionally rejects bad input.
            "consumers_count must be greater than or equal to 0",
        )

    old_symbols = {
        name: cast(TypedDictExtractedSymbol, symbol)
        for name, symbol in extract_symbols(old_source).items()
    }
    new_symbols = {
        name: cast(TypedDictExtractedSymbol, symbol)
        for name, symbol in extract_symbols(new_source).items()
    }

    old_names = set(old_symbols)
    new_names = set(new_symbols)

    changes: list[ModelSymbolChange] = []

    # Same-name symbols: classify by what changed
    for name in sorted(old_names & new_names):
        old_sym = old_symbols[name]
        new_sym = new_symbols[name]
        if old_sym["signature"] != new_sym["signature"]:
            changes.append(
                _make_change(
                    EnumChangeKind.SIGNATURE_CHANGE, name, file_path, consumers_count
                )
            )
        elif old_sym["body_hash"] != new_sym["body_hash"]:
            changes.append(
                _make_change(
                    EnumChangeKind.LOGIC_CHANGE, name, file_path, consumers_count
                )
            )
        # else: unchanged — no entry

    # Removed symbols
    removed = {name: old_symbols[name] for name in old_names - new_names}
    # Added symbols
    added = {name: new_symbols[name] for name in new_names - old_names}

    # Rename detection: pair removed R with added A if signatures match + line tolerance
    renamed_removed: set[str] = set()
    renamed_added: set[str] = set()
    for r_name, r_sym in sorted(removed.items()):
        r_sym = _symbol_with_name(r_sym, r_name)
        for a_name, a_sym in sorted(added.items()):
            if a_name in renamed_added:
                continue
            a_sym = _symbol_with_name(a_sym, a_name)
            if _rename_tolerance(r_sym, a_sym):
                changes.append(
                    _make_change(
                        EnumChangeKind.REFACTOR, a_name, file_path, consumers_count
                    )
                )
                renamed_removed.add(r_name)
                renamed_added.add(a_name)
                break

    # Remaining removed symbols
    for name in sorted(removed):
        if name in renamed_removed:
            continue
        kind = (
            EnumChangeKind.GUARD_REMOVED
            if _is_guard(name)
            else EnumChangeKind.DELETED_FUNCTION
        )
        changes.append(_make_change(kind, name, file_path, consumers_count))

    # Remaining added symbols
    for name in sorted(added):
        if name in renamed_added:
            continue
        changes.append(
            _make_change(EnumChangeKind.NEW_FUNCTION, name, file_path, consumers_count)
        )

    return ModelSemanticDiffReport(
        changes=tuple(changes),
        total_consumers_affected=consumers_count if changes else 0,
    )
