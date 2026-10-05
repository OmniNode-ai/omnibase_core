# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""JUnit artifact runtime with the original guard's CLI and exit codes.

Source and config reads pass through the gather EFFECT; report persistence passes
through the report-write EFFECT. The COMPUTE handler receives typed observations.
An optional --root discovers XML artifacts; no-artifact runs retain exit code 2.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping
from itertools import chain
from typing import SupportsInt, cast
from xml.parsers import expat

import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.integration_skips_check.model_integration_skip_record import (
    ModelIntegrationSkipRecord,
)
from omnibase_core.models.nodes.integration_skips_check.model_integration_skips_check_config import (
    ModelIntegrationSkipsCheckConfig,
)
from omnibase_core.models.nodes.integration_skips_check.model_integration_skips_check_input import (
    ModelIntegrationSkipsCheckInput,
)
from omnibase_core.models.nodes.integration_skips_check.model_integration_skips_raw_config import (
    ModelIntegrationSkipsRawConfig,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_integration_skips_check_compute.handler import (
    VALIDATOR_ID,
    NodeIntegrationSkipsCheckCompute,
    classify_skip,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = ["main"]


_JUNIT_PASS = '<?xml version="1.0" encoding="utf-8"?>\n<testsuites><testsuite name="pytest" tests="3" skipped="1">\n <testcase classname="tests.integration.runtime.db.test_postgres_repository_runtime_integration"\n   name="test_execute_select_returns_rows_against_real_postgres" time="0.1"/>\n <testcase classname="tests.integration.handlers.test_registration_storage_postgres_uuid_cast"\n   name="test_query_registrations_casts_node_id_uuid" time="0.1"/>\n <testcase classname="tests.integration.event_bus.test_kafka_boundary"\n   name="test_kafka_roundtrip">\n   <skipped type="pytest.skip" message="Redpanda broker not reachable at localhost:9092: connection refused"/>\n </testcase>\n</testsuite></testsuites>'

_JUNIT_SILENT_SKIP = '<?xml version="1.0" encoding="utf-8"?>\n<testsuites><testsuite name="pytest" tests="2" skipped="2">\n <testcase classname="tests.integration.runtime.db.test_postgres_repository_runtime_integration"\n   name="test_execute_select_returns_rows_against_real_postgres" time="0.0">\n   <skipped type="pytest.skip" message="PostgreSQL integration tests skipped: Missing OMNIBASE_INFRA_DB_URL or required POSTGRES_* fallback variables"/>\n </testcase>\n <testcase classname="tests.integration.handlers.test_registration_storage_postgres_uuid_cast"\n   name="test_query_registrations_casts_node_id_uuid" time="0.0">\n   <skipped type="pytest.skip" message="PostgreSQL not available (set OMNIBASE_INFRA_DB_URL or POSTGRES_HOST+POSTGRES_PASSWORD)"/>\n </testcase>\n</testsuite></testsuites>'


def _input_error(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.VALIDATION_ERROR
    )


def config_from_source(source: str) -> ModelIntegrationSkipsCheckConfig:
    """Extract the guard's operational keys, ignoring informational YAML keys."""
    try:
        document = load_yaml_content_as_model(source, ModelIntegrationSkipsRawConfig)
    except ModelOnexError as exc:
        prefix = "YAML parsing error: "
        if exc.message.startswith(prefix):
            raise yaml.YAMLError(exc.message[len(prefix) :]) from exc
        raise
    raw: Mapping[str, object] = document.model_dump(mode="json")
    services = cast(Mapping[str, object], raw.get("required_services") or {})
    required: dict[str, dict[str, object]] = {}
    for service, spec in services.items():
        entry = cast(Mapping[str, object], spec or {})
        required[service] = {
            "missing_skip_patterns": entry.get("missing_skip_patterns", [])
        }
    config = ModelIntegrationSkipsCheckConfig.model_validate(
        {
            "silent_skip_allowed": bool(raw.get("silent_skip_allowed", False)),
            "require_executed_min": int(
                cast(SupportsInt, raw.get("require_executed_min", 1))
            ),
            "required_services": required,
            "allowed_optional_skip_patterns": raw.get("allowed_optional_skip_patterns")
            or [],
        }
    )
    for spec in config.required_services.values():
        for pattern in spec.missing_skip_patterns:
            re.compile(pattern, re.IGNORECASE)
    for pattern in config.allowed_optional_skip_patterns:
        re.compile(pattern, re.IGNORECASE)
    return config


def _expanded_name(name: str) -> str:
    return "{" + name if "}" in name else name


def _parse_xml(source: str) -> tuple[ET.Element, list[int]]:
    """Build an ElementTree with Expat's source locations in a single pass."""
    parser = expat.ParserCreate(namespace_separator="}")
    builder = ET.TreeBuilder()
    lines: list[int] = []

    def start_element(tag: str, attrs: dict[str, str]) -> None:
        if tag == "testcase":
            lines.append(parser.CurrentLineNumber)
        builder.start(
            _expanded_name(tag), {_expanded_name(k): v for k, v in attrs.items()}
        )

    def end_element(tag: str) -> None:
        builder.end(_expanded_name(tag))

    parser.StartElementHandler = start_element
    parser.EndElementHandler = end_element
    parser.CharacterDataHandler = builder.data
    parser.Parse(source, True)
    return builder.close(), lines


def input_from_sources(
    files: Iterable[ModelSourceFile],
    config: ModelIntegrationSkipsCheckConfig,
    *,
    strict: bool = False,
) -> ModelIntegrationSkipsCheckInput:
    """Parse testcase observations; failed and errored testcases count as executed."""
    executed = 0
    total = 0
    records: list[ModelIntegrationSkipRecord] = []
    for file in files:
        try:
            root, lines = _parse_xml(file.source)
        except expat.ExpatError as exc:
            raise _input_error(
                f"could not parse JUnit report {file.path}: {exc}"
            ) from exc
        for case, line in zip(root.iter("testcase"), lines, strict=True):
            total += 1
            skipped = case.find("skipped")
            if skipped is None:
                executed += 1
                continue
            classname = case.get("classname", "")
            name = case.get("name", "")
            label = f"{classname}::{name}" if classname else name
            reason = (skipped.get("message", "") or (skipped.text or "")).strip()
            records.append(
                ModelIntegrationSkipRecord(
                    test_name=label, reason=reason, path=file.path, line=line
                )
            )
    return ModelIntegrationSkipsCheckInput(
        executed=executed,
        total_cases=total,
        skipped=tuple(records),
        config=config,
        strict=strict,
    )


def _gather(
    paths: list[str], *, root: str = ".", config: bool = False
) -> list[ModelSourceFile]:
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=root,
            explicit_paths=paths,
            include_patterns=["*"] if paths else ["**/*.xml"],
            max_file_size=0,
        )
    )
    for skipped in output.skipped:
        if paths or skipped.reason.startswith(
            ("read error:", "error checking file size:")
        ):
            if skipped.reason == "not a file":
                message = (
                    str(FileNotFoundError(2, "No such file or directory", skipped.path))
                    if config
                    else f"JUnit report not found: {skipped.path}"
                )
            else:
                message = skipped.reason.removeprefix("read error: ").removeprefix(
                    "error checking file size: "
                )
            if skipped.reason.startswith(("read error:", "error checking file size:")):
                raise ModelOnexError(
                    message=message, error_code=EnumCoreErrorCode.FILE_READ_ERROR
                )
            raise _input_error(message)
    return [
        ModelSourceFile(path=file.path, source=file.source) for file in output.files
    ]


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def _error(message: str, report_path: str | None) -> int:
    report = ModelValidationReport.from_runtime_errors(VALIDATOR_ID, (message,))
    _write_report(report_path, report)
    sys.stdout.write(f"::error::{message}\n")
    return 2


def _display(
    request: ModelIntegrationSkipsCheckInput, report: ModelValidationReport
) -> int:
    sys.stdout.write("=== integration silent-skip guard (OMN-14172) ===\n")
    sys.stdout.write(
        f"cases={request.total_cases} executed={request.executed} skipped={len(request.skipped)} require_executed_min={request.config.require_executed_min}\n"
    )
    for record in request.skipped:
        offending, allowed = classify_skip(record.reason, request.config)
        tag = (
            f"BAD[{offending}]"
            if offending
            else ("ok-optional" if allowed else "ok-unclassified")
        )
        sys.stdout.write(f"  skip {tag}: {record.test_name} :: {record.reason}\n")
    if report.findings:
        sys.stdout.write("\nGATE FAILED — silent-skip false-green(s) detected:\n")
        for finding in report.findings:
            sys.stdout.write(f"::error::{finding.message}\n")
        return 1
    sys.stdout.write(
        "\nGATE PASSED — no missing-service silent-skips; integration tests ran.\n"
    )
    return 0


def _selftest(
    config: ModelIntegrationSkipsCheckConfig,
) -> tuple[int, ModelValidationReport]:
    handler = NodeIntegrationSkipsCheckCompute()
    good = handler.handle(
        input_from_sources(
            [ModelSourceFile(path="pass.xml", source=_JUNIT_PASS)], config
        )
    )
    bad = handler.handle(
        input_from_sources(
            [ModelSourceFile(path="skip.xml", source=_JUNIT_SILENT_SKIP)], config
        )
    )
    errors: list[str] = []
    if good.findings:
        message = f"SELFTEST FAIL (case a should pass): {[finding.message for finding in good.findings]}"
        errors.append(message)
        sys.stdout.write(message + "\n")
    else:
        sys.stdout.write("SELFTEST ok: case (a) provisioned -> PASS\n")
    if not bad.findings:
        message = "SELFTEST FAIL (case b should be RED): gate did not flag silent skip"
        errors.append(message)
        sys.stdout.write(message + "\n")
    else:
        sys.stdout.write(
            f"SELFTEST ok: case (b) silent-skip -> RED ({len(bad.findings)} violation(s))\n"
        )
    if not config.required_services:
        message = "SELFTEST FAIL: config declares no required_services"
        errors.append(message)
        sys.stdout.write(message + "\n")
    if config.silent_skip_allowed:
        message = "SELFTEST FAIL: silent_skip_allowed must be false"
        errors.append(message)
        sys.stdout.write(message + "\n")
    sys.stdout.write("SELFTEST FAILED\n" if errors else "SELFTEST PASSED\n")
    report = ModelValidationReport.from_findings(
        findings=tuple(
            ModelValidationFindingEmbed(
                validator_id=VALIDATOR_ID,
                severity="FAIL",
                rule_id="selftest",
                location="<selftest>:1",
                message=message,
            )
            for message in errors
        ),
        request=ModelValidationRequestRef(profile="default"),
        validators_run=(VALIDATOR_ID,),
    )
    return (1 if errors else 0), report


def main(argv: list[str] | None = None) -> int:
    """Run the guard: 0 passed, 1 false-green, 2 usage or input error."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filenames", nargs="*", help="Explicit JUnit artifacts")
    parser.add_argument("--junit", nargs="+", help="JUnit-XML report(s)")
    parser.add_argument("--config", default="scripts/ci/integration_skip_guard.yaml")
    parser.add_argument(
        "--strict", action="store_true", help="Fail on unclassified reasons"
    )
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--root", help="Discover JUnit XML artifacts recursively")
    parser.add_argument("--report-json", help="Write the canonical validation report")
    args = parser.parse_args(argv)
    try:
        source = _gather([args.config], config=True)[0].source
        config = config_from_source(source)
    except (ModelOnexError, OSError, yaml.YAMLError, re.error, ValidationError) as exc:
        detail = exc.message if isinstance(exc, ModelOnexError) else str(exc)
        return _error(
            f"could not load guard config {args.config}: {detail}", args.report_json
        )
    if args.selftest:
        code, report = _selftest(config)
        _write_report(args.report_json, report)
        return code
    paths = args.junit or args.filenames
    if not paths and args.root is None:
        return _error("--junit is required (or use --selftest)", args.report_json)
    try:
        files = (
            (file for path in paths for file in _gather([path]))
            if paths
            else iter(_gather([], root=args.root or "."))
        )
        first = next(files, None)
        if first is None:
            return _error("--junit is required (or use --selftest)", args.report_json)
        request = input_from_sources(chain((first,), files), config, strict=args.strict)
    except ModelOnexError as exc:
        if exc.error_code != EnumCoreErrorCode.FILE_READ_ERROR:
            return _error(exc.message, args.report_json)
        report = ModelValidationReport.from_runtime_errors(VALIDATOR_ID, (exc.message,))
        _write_report(args.report_json, report)
        sys.stderr.write(exc.message + "\n")
        return 1
    except (UnicodeError, expat.ExpatError) as exc:
        return _error(
            str(exc),
            args.report_json,
        )
    report = NodeIntegrationSkipsCheckCompute().handle(request)
    _write_report(args.report_json, report)
    return _display(request, report)


if __name__ == "__main__":
    sys.exit(main())
