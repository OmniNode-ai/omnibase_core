# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Bind legacy detectors to HandlerFindingBaseline without global allowances.

Slice A deliberately retains the existing predicates. This runtime adapts their
findings to the shared per-file, source-identity baseline. Hooks never write it;
the explicit --write-baseline maintenance operation only removes entries.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import importlib.util
import json
import subprocess
import sys
from collections.abc import Sequence
from functools import cache
from importlib import resources
from pathlib import Path
from types import ModuleType

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.finding_baseline.model_finding_detect_result import (
    ModelFindingDetectResult,
)
from omnibase_core.models.finding_baseline.model_legacy_ratchet_rule import (
    ModelLegacyRatchetRule,
)
from omnibase_core.models.finding_baseline.model_legacy_ratchet_rules import (
    ModelLegacyRatchetRules,
)
from omnibase_core.models.finding_baseline.model_source_finding import (
    ModelSourceFinding,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.nodes.node_finding_baseline_check_effect.runtime_finding_baseline_check import (
    run_baselined_hook,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model


@cache
def load_rules() -> ModelLegacyRatchetRules:
    """Read the adapter bindings shipped with core."""
    raw = resources.files("omnibase_core.contracts").joinpath(
        "legacy_ratchet_rules.yaml"
    )
    return load_yaml_content_as_model(raw.read_text("utf-8"), ModelLegacyRatchetRules)


@cache
def _module(name: str) -> ModuleType:
    if not name.endswith(".py"):
        return importlib.import_module(name)
    # These repository scripts predate Slice A. Their full predicate migration
    # is a later slice; loading is isolated at this existing effect boundary.
    root = Path(__file__).resolve().parents[4]
    spec = importlib.util.spec_from_file_location(Path(name).stem, root / name)
    if spec is None or spec.loader is None:
        raise ModelOnexError(
            message=f"Cannot load detector {name}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _finding(
    source: ModelSourceFile,
    line: int,
    rule: str,
    message: str,
    *,
    baselinable: bool = True,
) -> ModelSourceFinding:
    lines = source.source.splitlines()
    return ModelSourceFinding(
        path=source.path,
        line=line,
        rule=rule,
        text="sha256:"
        + hashlib.sha256(
            (
                " ".join(lines[line - 1].split()) if 0 < line <= len(lines) else ""
            ).encode("utf-8")
        ).hexdigest(),
        message=message,
        baselinable=baselinable,
    )


def detect_sources(
    rule: ModelLegacyRatchetRule, sources: tuple[ModelSourceFile, ...]
) -> ModelFindingDetectResult:
    """Adapt existing AST visitors, preserving their finding granularity."""
    module = _module(rule.module)
    checker_type = getattr(module, rule.checker)
    findings: list[ModelSourceFinding] = []
    for source in sources:
        path = Path(source.path)
        if set(path.parts).intersection(rule.exclude_parts) or source.path.startswith(
            rule.exclude_prefixes
        ):
            continue
        try:
            tree = ast.parse(source.source, filename=source.path)
        except SyntaxError as exc:
            findings.append(
                _finding(
                    source, exc.lineno or 0, "syntax-error", str(exc), baselinable=False
                )
            )
            continue
        if rule.hook.startswith("substrate-"):
            for item in checker_type().check_tree(
                tree, source.source.splitlines(), path
            ):
                findings.append(_finding(source, item.line, rule.hook, item.message))
        elif rule.hook == "validate-stubbed-functionality":
            if module.ONEXStubbedFunctionalityValidator().is_allowed_file(path):
                continue
            checker = checker_type(source.path)
            checker.visit(tree)
            for line, message in checker.issues:
                findings.append(_finding(source, line, rule.hook, message))
        elif rule.hook == "validate-model-dump-json-mode":
            checker = checker_type(source.source.splitlines())
            checker.visit(tree)
            for item in checker.violations:
                findings.append(
                    _finding(source, item["line"], item["type"], item["message"])
                )
        elif rule.hook == "validate-union-usage":
            checker = checker_type(source.path, source.source)
            checker.visit(tree)
            for pattern in checker.invalid_patterns:
                findings.append(
                    _finding(
                        source,
                        pattern.line,
                        rule.hook,
                        "Invalid union: " + pattern.get_signature(),
                    )
                )
    return ModelFindingDetectResult(
        findings=tuple(findings), files_checked=len(sources)
    )


def detect_pyright(
    rule: ModelLegacyRatchetRule, project: str, sources: tuple[ModelSourceFile, ...]
) -> ModelFindingDetectResult:
    """Run pyright once per batch; only the three new rules are baselinable."""
    if not sources:
        return ModelFindingDetectResult()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyright",
            "--outputjson",
            "--project",
            project,
            *(source.path for source in sources),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    by_path = {Path(s.path).resolve(): s for s in sources}
    try:
        document = json.loads(result.stdout)
        diagnostics = document["generalDiagnostics"]
        if result.returncode not in (0, 1) or not isinstance(diagnostics, list):
            raise ModelOnexError(
                message="pyright did not return diagnostics",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
    except (ValueError, KeyError, TypeError, ModelOnexError) as exc:
        return ModelFindingDetectResult(
            findings=(
                _finding(
                    sources[0],
                    0,
                    "pyright-error",
                    f"{exc}: {result.stderr or result.stdout}",
                    baselinable=False,
                ),
            )
        )
    findings: list[ModelSourceFinding] = []
    for diagnostic in diagnostics:
        if diagnostic["severity"] != "error":
            sys.stderr.write(
                f"{diagnostic['severity']}: {diagnostic['file']}: {diagnostic['message']}\n"
            )
            continue
        source = by_path.get(Path(diagnostic["file"]).resolve())
        if source is None:
            # Never silently discard an error reached through an imported file.
            source = ModelSourceFile(path=diagnostic["file"], source="")
        code = diagnostic.get("rule", "pyright-error")
        findings.append(
            _finding(
                source,
                diagnostic["range"]["start"]["line"] + 1,
                code,
                diagnostic["message"],
                baselinable=code in rule.diagnostic_rules,
            )
        )
    if result.returncode and not findings:
        findings.append(
            _finding(
                sources[0],
                0,
                "pyright-error",
                result.stderr or "pyright failed without an error diagnostic",
                baselinable=False,
            )
        )
    return ModelFindingDetectResult(
        findings=tuple(findings), files_checked=len(sources)
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Select a contract binding, then use the shared baseline runtime."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--hook", required=True, choices=[r.hook for r in load_rules().rules]
    )
    parser.add_argument("--project", default=load_rules().pyright_project)
    parsed, remaining = parser.parse_known_args(argv)
    remaining = [name for name in remaining if name != parsed.project]
    rule = next(r for r in load_rules().rules if r.hook == parsed.hook)

    def detect(sources: tuple[ModelSourceFile, ...]) -> ModelFindingDetectResult:
        if rule.hook == "pyright-type-check":
            return detect_pyright(rule, parsed.project, sources)
        return detect_sources(rule, sources)

    return run_baselined_hook(
        remaining,
        hook_id=rule.hook,
        description="Refuse new findings and stale baseline entries, per file.",
        detect=detect,
        remediation="Fix the finding; remove stale baseline entries with --write-baseline.",
        default_dirs=load_rules().default_dirs,
        skip_dir_parts=frozenset(rule.exclude_parts),
    )


if __name__ == "__main__":
    sys.exit(main())
