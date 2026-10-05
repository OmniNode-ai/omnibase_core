# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Original skip-count CLI, with file reads and report writes at EFFECT boundaries.

Exit codes remain 0 (PASS), 1 (growth), 2 (invalid input). Newly rejected
zero-record or unreadable inventories exit 1. No baseline override exists.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal, cast
from xml.parsers import expat

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_baseline_entry import (
    ModelSkipCountBaselineEntry,
)
from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_observation import (
    ModelSkipCountObservation,
)
from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_ratchet_check_input import (
    ModelSkipCountRatchetCheckInput,
)
from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_record import (
    ModelSkipCountRecord,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_skip_count_ratchet_check_compute.handler import (
    NodeSkipCountRatchetCheckCompute,
)
from omnibase_core.nodes.node_skip_count_ratchet_check_compute.ratchet_decision import (
    VALIDATOR_ID,
    ZERO_RECORDS_MESSAGE,
    evaluate,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)

_DEFAULT_BASELINE = (
    Path(__file__).resolve().parents[4] / "config" / "skip_count_baseline.yaml"
)
_REQUIRED_PROVENANCE_FIELDS = ("measured_at", "measurement_command", "source_runs")
_MODES = ("count", "nodeids")


def _input_error(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.VALIDATION_ERROR
    )


def _integer(value: object) -> int:
    if isinstance(value, (str, int, float)):
        return int(value)
    raise _input_error("not an integer")


def canonical_node_id(raw: str) -> str:
    return raw[6:] if raw.startswith("tests.") else raw


def _read(path: Path, kind: str) -> ModelSourceFile:
    try:
        output = NodeSourceFileGatherEffect().handle(
            ModelSourceFileGatherInput(
                root=".", explicit_paths=[str(path)], include_patterns=["*"]
            )
        )
    except (OSError, UnicodeError) as exc:
        raise _input_error(f"read error: {path}: {exc}") from exc
    if output.files:
        return ModelSourceFile(path=output.files[0].path, source=output.files[0].source)
    if output.skipped and output.skipped[0].reason.startswith("read error:"):
        raise _input_error(f"read error: {path}: {output.skipped[0].reason[12:]}")
    raise _input_error(f"{kind} not found: {path}")


def from_yaml_baseline_content(
    file: ModelSourceFile, key: str
) -> ModelSkipCountBaselineEntry:
    """Parse and validate a foreign baseline before constructing the typed entry."""
    path = file.path
    try:
        raw: object = yaml.safe_load(file.source)
    except yaml.YAMLError as exc:
        raise _input_error(f"baseline file is not parsable YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise _input_error(f"baseline file is not a mapping: {path}")
    suites = raw.get("suites")
    if not isinstance(suites, dict):
        raise _input_error(f"baseline file declares no `suites` mapping: {path}")
    entry = suites.get(key)
    if not isinstance(entry, dict):
        raise _input_error(
            f"suite {key!r} is not registered in {path}. "
            f"Registered suites: {', '.join(sorted(suites)) or '(none)'}"
        )

    provenance = entry.get("provenance")
    if not isinstance(provenance, dict):
        raise _input_error(
            f"suite {key!r} carries no provenance block. A baseline number "
            f"with no recorded measurement is a claim, not a measurement."
        )
    for field in _REQUIRED_PROVENANCE_FIELDS:
        if not provenance.get(field):
            raise _input_error(f"suite {key!r}: provenance.{field} is missing or empty")

    mode = str(entry.get("mode", ""))
    if mode not in _MODES:
        raise _input_error(f"suite {key!r}: mode must be one of {_MODES}, got {mode!r}")
    node_ids = entry.get("node_ids") or []
    if not isinstance(node_ids, list):
        raise _input_error(f"suite {key!r}: node_ids must be a list")
    if mode == "nodeids" and not node_ids:
        raise _input_error(
            f"suite {key!r}: mode `nodeids` needs a recorded node_ids set"
        )
    try:
        max_skips = _integer(entry["max_skips"])
        baseline_collected = _integer(entry["baseline_collected"])
    except (KeyError, TypeError, ValueError, ModelOnexError) as exc:
        raise _input_error(
            f"suite {key!r}: max_skips and baseline_collected must both be integers"
        ) from exc
    if mode == "nodeids" and max_skips != len(set(node_ids)):
        raise _input_error(
            f"suite {key!r}: max_skips ({max_skips}) disagrees with the recorded "
            f"node_ids set ({len(set(node_ids))} unique). The two must be written "
            f"together or the count half of the report lies."
        )
    repo = str(entry.get("repo", "") or "")
    job = str(entry.get("job", "") or "")
    if not repo or not job:
        raise _input_error(f"suite {key!r}: both `repo` and `job` are required")

    return ModelSkipCountBaselineEntry(
        key=key,
        repo=repo,
        job=job,
        mode=cast(Literal["count", "nodeids"], mode),
        max_skips=max_skips,
        baseline_collected=baseline_collected,
        node_ids=frozenset(canonical_node_id(str(i)) for i in node_ids),
        path=path,
    )


def load_baseline(path: Path, key: str) -> ModelSkipCountBaselineEntry:
    return from_yaml_baseline_content(_read(path, "baseline file"), key)


def observe_content(files: list[ModelSourceFile]) -> ModelSkipCountObservation:
    if not files:
        raise _input_error("no JUnit reports named; refusing to report a verdict")
    records: list[ModelSkipCountRecord] = []
    collected = 0
    for file in files:
        try:
            builder = ET.TreeBuilder()
            parser = expat.ParserCreate()
            parser.StartElementHandler = builder.start
            parser.EndElementHandler = builder.end
            parser.CharacterDataHandler = builder.data
            parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
            parser.Parse(file.source, True)
            root = builder.close()
        except (ET.ParseError, expat.ExpatError) as exc:
            raise _input_error(
                f"JUnit report is not parsable XML: {file.path}: {exc}"
            ) from exc
        for suite in root.iter("testsuite"):
            try:
                collected += int(suite.get("tests", 0) or 0)
            except ValueError as exc:
                raise _input_error(
                    f"{file.path}: testsuite/@tests is not an integer"
                ) from exc
        for testcase in root.iter("testcase"):
            classname = (testcase.get("classname") or "").strip()
            name = (testcase.get("name") or "").strip()
            identity = f"{classname}::{name}" if classname else name
            records.append(
                ModelSkipCountRecord(
                    identity=identity, skipped=testcase.find("skipped") is not None
                )
            )
    return ModelSkipCountObservation(
        records=tuple(records), collected=collected, files=len(files)
    )


def observe(paths: list[Path]) -> ModelSkipCountObservation:
    if not paths:
        raise _input_error("no JUnit reports named; refusing to report a verdict")
    return observe_content([_read(path, "JUnit report") for path in paths])


def render_observed(entry_key: str, observed: ModelSkipCountObservation) -> str:
    return yaml.safe_dump(
        {
            "suites": {
                entry_key: {
                    "max_skips": observed.count,
                    "baseline_collected": observed.collected,
                    "node_ids": sorted(observed.skipped),
                }
            }
        },
        sort_keys=True,
        default_flow_style=False,
    )


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def _error(message: str, destination: str | None, code: int) -> int:
    line = f"::error::skip-count-ratchet input error (fail-closed): {message}"
    report = ModelValidationReport.from_runtime_errors(VALIDATOR_ID, (line,))
    _write_report(destination, report)
    sys.stdout.write(line + "\n")
    return code


def _selftest() -> tuple[int, ModelValidationReport]:
    """Exercise the same six verdicts and three input refusals without disk writes."""
    baseline_ids = ["pkg.mod_a::test_one", "pkg.mod_b::test_two"]
    failures: list[str] = []
    for mode, ids, collected, expected in (
        ("nodeids", baseline_ids, 100, "PASS"),
        ("nodeids", [*baseline_ids, "pkg.mod_c::test_new"], 100, "FAIL"),
        ("nodeids", baseline_ids[:1], 40, "PASS"),
        ("nodeids", baseline_ids[:1], 100, "PASS"),
        ("count", baseline_ids, 100, "PASS"),
        ("count", [*baseline_ids, "pkg.mod_c::test_new"], 100, "FAIL"),
    ):
        entry = ModelSkipCountBaselineEntry(
            key=f"selftest/{mode}",
            repo="selftest",
            job="Selftest" if mode == "nodeids" else "Selftest Count",
            mode=cast(Literal["count", "nodeids"], mode),
            max_skips=2,
            baseline_collected=100,
            node_ids=frozenset(baseline_ids) if mode == "nodeids" else frozenset(),
            path="selftest/baseline.yaml",
        )
        observed = ModelSkipCountObservation(
            records=tuple(ModelSkipCountRecord(identity=i, skipped=True) for i in ids),
            collected=collected,
            files=1,
        )
        report = NodeSkipCountRatchetCheckCompute().handle(
            ModelSkipCountRatchetCheckInput(baseline=entry, observation=observed)
        )
        if report.overall_status != expected:
            failures.append(f"{mode}: expected {expected}, got {report.overall_status}")
    for paths in ([Path("selftest/absent.xml")], []):
        try:
            observe(paths)
        except ModelOnexError:
            continue
        failures.append("a fail-closed input was accepted")
    bare = ModelSourceFile(
        path="selftest/bare.yaml",
        source="suites:\n  bare/entry: {repo: r, job: j, mode: count, max_skips: 0, baseline_collected: 0}",
    )
    try:
        from_yaml_baseline_content(bare, "bare/entry")
    except ModelOnexError:
        pass
    else:
        failures.append("a provenance-less baseline entry was accepted")
    shipped = 0
    if _DEFAULT_BASELINE.is_file():
        source = _read(_DEFAULT_BASELINE, "baseline file")
        keys = from_yaml_baseline_keys(source)
        if not keys:
            failures.append(f"{_DEFAULT_BASELINE} registers no suites")
        for key in keys:
            try:
                from_yaml_baseline_content(source, key)
            except ModelOnexError as exc:
                failures.append(f"shipped baseline suite {key!r}: {exc.message}")
            else:
                shipped += 1
    if failures:
        sys.stdout.write("skip-count-ratchet selftest FAILED:\n")
        for line in failures:
            sys.stdout.write(f"  - {line}\n")
        return 1, ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, tuple(failures)
        )
    sys.stdout.write(
        f"skip-count-ratchet selftest OK: 6 verdict cases, 3 fail-closed cases, {shipped} shipped baseline suite(s) validated.\n"
    )
    return 0, ModelValidationReport.from_findings(
        findings=(),
        request=ModelValidationRequestRef(profile="default"),
        validators_run=(VALIDATOR_ID,),
    )


def from_yaml_baseline_keys(file: ModelSourceFile) -> list[str]:
    """Identify registered entries for shipped-baseline selftest validation."""
    raw: object = yaml.safe_load(file.source)
    if not isinstance(raw, dict):
        return []
    suites = raw.get("suites")
    if not isinstance(suites, dict):
        return []
    return [str(key) for key in suites]


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.selftest:
            code, report = _selftest()
            _write_report(args.report_json, report)
            return code
        if not args.suite:
            raise _input_error("--suite is required")
        paths = [*args.junit, *(Path(p) for p in args.filenames)]
        if not paths and args.root is not None:
            output = NodeSourceFileGatherEffect().handle(
                ModelSourceFileGatherInput(
                    root=args.root, include_patterns=["**/*.xml"], max_file_size=0
                )
            )
            read_errors = [
                f"{skipped.path}: {skipped.reason}"
                for skipped in output.skipped
                if skipped.reason.startswith(
                    ("read error:", "error checking file size:")
                )
            ]
            if read_errors:
                return _error(
                    "; ".join(read_errors),
                    args.report_json,
                    1,
                )
            if not output.files:
                return _error(
                    f"zero files scanned under {args.root}: a full-tree run that scans nothing is ERROR, never PASS",
                    args.report_json,
                    1,
                )
            observed = observe_content(
                [ModelSourceFile(path=f.path, source=f.source) for f in output.files]
            )
        else:
            observed = observe(paths)
        if observed.test_records == 0:
            return _error(ZERO_RECORDS_MESSAGE, args.report_json, 1)
        if args.print_observed:
            sys.stdout.write(render_observed(args.suite, observed) + "\n")
            report = ModelValidationReport.from_findings(
                findings=(),
                request=ModelValidationRequestRef(profile="default"),
                validators_run=(VALIDATOR_ID,),
            )
            _write_report(args.report_json, report)
            return 0
        entry = load_baseline(args.baseline, args.suite)
    except ModelOnexError as exc:
        return _error(
            exc.message,
            args.report_json,
            1 if exc.message.startswith("read error:") else 2,
        )
    except (OSError, UnicodeError) as exc:
        return _error(f"read error: {exc}", args.report_json, 1)
    report = NodeSkipCountRatchetCheckCompute().handle(
        ModelSkipCountRatchetCheckInput(baseline=entry, observation=observed)
    )
    _write_report(args.report_json, report)
    _, lines = evaluate(entry, observed)
    sys.stdout.write("\n".join(lines) + "\n")
    return 0 if report.overall_status == "PASS" else 1


def _build_parser() -> argparse.ArgumentParser:
    """The parser declares no lever that lowers a verdict. That is load-bearing."""
    parser = argparse.ArgumentParser(
        prog="skip_count_ratchet.py",
        description=(
            "Refuse a run whose set of never-executed tests grew beyond the "
            "recorded baseline. Lowering a baseline is an edit to the baseline "
            "file, never a flag on this command."
        ),
    )
    parser.add_argument(
        "--suite",
        help="baseline key for the suite under test, e.g. omnibase_core/tests-integration",
    )
    parser.add_argument(
        "--junit",
        nargs="+",
        default=[],
        type=Path,
        help="pytest JUnit-XML report(s) produced by that suite's run",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=_DEFAULT_BASELINE,
        help="path to the baseline file (default: config/skip_count_baseline.yaml)",
    )
    parser.add_argument(
        "--print-observed",
        action="store_true",
        help=(
            "print the observed set as a baseline-shaped YAML block for a human to "
            "paste; reaches no verdict and writes no file"
        ),
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="run the gate's own logic over synthetic reports (what pre-commit runs)",
    )
    parser.add_argument(
        "filenames", nargs="*", help="Explicit JUnit reports (alternative to --junit)"
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Gather JUnit XML reports recursively when no reports are named",
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help="Write the canonical validation report through the report-write EFFECT",
    )
    return parser


if __name__ == "__main__":
    sys.exit(main())
