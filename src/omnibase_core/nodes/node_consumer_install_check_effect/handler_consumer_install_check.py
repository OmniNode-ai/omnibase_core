# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""EFFECT handler: install a candidate build into consumer checkouts and import them (OMN-26670).

For every consumer the overlay names for the candidate: check out the overlay ref, build a
throwaway venv, install the consumer, replace the candidate with the build under test, import
every entry point of the consumer, collect its unit tests, and turn each failure into a finding
that names the consumer, the import and the missing name. The consumer list, refs, commands'
arguments and every bound come from the overlay; this module holds none of them.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.consumer_install_check.model_candidate_spec import (
    ModelCandidateSpec,
)
from omnibase_core.models.nodes.consumer_install_check.model_command_request import (
    ModelCommandRequest,
)
from omnibase_core.models.nodes.consumer_install_check.model_consumer_finding import (
    ModelConsumerFinding,
)
from omnibase_core.models.nodes.consumer_install_check.model_consumer_install_overlay import (
    ModelConsumerInstallOverlay,
)
from omnibase_core.models.nodes.consumer_install_check.model_consumer_install_request import (
    ModelConsumerInstallRequest,
)
from omnibase_core.models.nodes.consumer_install_check.model_consumer_install_result import (
    ModelConsumerInstallResult,
)
from omnibase_core.models.nodes.consumer_install_check.model_consumer_outcome import (
    ModelConsumerOutcome,
)
from omnibase_core.models.nodes.consumer_install_check.model_consumer_spec import (
    ModelConsumerSpec,
)
from omnibase_core.nodes.node_consumer_install_check_effect.exec_subprocess import (
    HandlerSubprocessExec,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

__all__ = [
    "HandlerConsumerInstallCheck",
    "load_overlay",
    "parse_collection_output",
    "parse_smoke_output",
]

FAILURE_PREFIX = "CONSUMER-INSTALL-CHECK FAIL "
_TAIL_CHARS = 1500
_COLLECTED = re.compile(r"(\d+) tests? collected")
_ERROR_HEADER = re.compile(r"^_+ ERROR collecting (?P<path>\S+) _+$", re.MULTILINE)
_SUMMARY_HEADER = re.compile(r"^=+ short test summary info =+$", re.MULTILINE)
_LOCATION = re.compile(r"^(?P<file>[^\s:]+):(?P<line>\d+): in <module>$", re.MULTILINE)
_IMPORT_LINE = re.compile(
    r"^ {4}(?P<stmt>(?:from\s+\S+\s+import\s.*|import\s.*))$", re.MULTILINE
)
_ERROR_LINE = re.compile(r"^E\s+(?P<type>\w+): (?P<msg>.*)$", re.MULTILINE)
_MISSING_MODULE = re.compile(r"No module named '(?P<mod>[^']+)'")
_SMOKE_FAIL = re.compile(
    r"^LATEST-CORE-SMOKE FAIL node=(?P<node>\S+) module=(?P<module>\S+) symbol=(?P<symbol>.+?) at=(?P<at>\S+) error=(?P<error>.*)$",
    re.MULTILINE,
)
_CANNOT_IMPORT = re.compile(
    r"cannot import name '(?P<name>[^']+)' from '(?P<mod>[^']+)'"
)


def load_overlay(path: Path) -> ModelConsumerInstallOverlay:
    """Read and validate the overlay; an unreadable or malformed one raises."""
    try:
        document = load_yaml_mapping_no_duplicates(
            path.read_text(encoding="utf-8"), source=str(path)
        )
    except (OSError, ValueError) as exc:
        raise ModelOnexError(
            message=f"consumer install overlay unreadable: {path}: {exc}",
            error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
        ) from exc
    return ModelConsumerInstallOverlay.model_validate(document)


def _probe_script() -> Path:
    return Path(__file__).with_name("runtime_entry_point_probe.py")


def _touches(roots: tuple[str, ...], *texts: str) -> bool:
    return any(
        text == root
        or text.startswith(f"{root}.")
        or f"/{root}/" in text
        or f" {root}." in text
        for root in roots
        for text in texts
    )


def _missing_from(message: str, type_name: str) -> str:
    cannot = _CANNOT_IMPORT.search(message)
    if cannot:
        return f"{cannot['mod']}.{cannot['name']}"
    missing = _MISSING_MODULE.search(message)
    if missing:
        return missing["mod"]
    return f"{type_name}: {message[:200]}"


def parse_collection_output(
    consumer: str, output: str, roots: tuple[str, ...]
) -> tuple[int, tuple[ModelConsumerFinding, ...]]:
    """Count the tests collected and turn each collection error into a finding."""
    counted = _COLLECTED.search(output)
    count = int(counted[1]) if counted else 0
    headers = list(_ERROR_HEADER.finditer(output))
    summary = _SUMMARY_HEADER.search(output)
    findings: list[ModelConsumerFinding] = []
    for position, header in enumerate(headers):
        end = (
            headers[position + 1].start()
            if position + 1 < len(headers)
            else (summary.start() if summary else len(output))
        )
        block = output[header.end() : end]
        statements = list(_IMPORT_LINE.finditer(block))
        locations = list(_LOCATION.finditer(block))
        error = _ERROR_LINE.search(block)
        statement = (
            statements[-1]["stmt"].strip()
            if statements
            else f"collecting {header['path']}"
        )
        if statements and locations:
            where = locations[-1]
            statement = f"{statement} ({where['file']}:{where['line']})"
        missing = (
            _missing_from(error["msg"], error["type"])
            if error
            else "<collection error without a message>"
        )
        findings.append(
            ModelConsumerFinding(
                consumer=consumer,
                stage="collection",
                import_statement=statement,
                missing_name=missing,
                detail=header["path"],
                attributed_to_candidate=_touches(roots, missing, statement, block),
            )
        )
    return count, tuple(findings)


def parse_smoke_output(
    consumer: str, output: str, roots: tuple[str, ...]
) -> tuple[ModelConsumerFinding, ...]:
    """Turn the consumer's own smoke script failure lines into findings."""
    return tuple(
        ModelConsumerFinding(
            consumer=consumer,
            stage="smoke",
            import_statement=f"import {m['module']} ({m['at']})",
            missing_name=m["symbol"],
            detail=f"node {m['node']}: {m['error'][:200]}",
            attributed_to_candidate=_touches(roots, m["symbol"], m["error"]),
        )
        for m in _SMOKE_FAIL.finditer(output)
    )


class HandlerConsumerInstallCheck:
    """Drive the checkout, install, import and collection of every consumer of one candidate."""

    def __init__(self, container: ModelONEXContainer) -> None:
        self._exec = container.get_service(HandlerSubprocessExec)

    def handle(
        self, request: ModelConsumerInstallRequest
    ) -> ModelConsumerInstallResult:
        """Check the candidate against every consumer the overlay names for it."""
        overlay = load_overlay(request.overlay_path)
        candidate = next(
            (
                c
                for c in overlay.candidates
                if c.distribution == request.candidate_distribution
            ),
            None,
        )
        if candidate is None:
            raise ModelOnexError(
                message=f"overlay names no candidate {request.candidate_distribution!r}",
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            )
        by_name = {c.name: c for c in overlay.consumers}
        missing = [name for name in candidate.consumers if name not in by_name]
        if missing:
            raise ModelOnexError(
                message=f"candidate {candidate.distribution!r} names consumers the overlay lacks: {missing}",
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            )
        refs: dict[str, str] = dict(request.consumer_ref_overrides)
        specs = [by_name[name] for name in candidate.consumers]
        started = time.monotonic()

        def check(spec: ModelConsumerSpec) -> ModelConsumerOutcome:
            ref = refs.get(spec.name) or spec.ref
            return self._check_one(spec, ref, request, overlay, candidate)

        with ThreadPoolExecutor(max_workers=overlay.max_parallel) as pool:
            outcomes = tuple(pool.map(check, specs))
        elapsed = time.monotonic() - started
        lines = tuple(
            line
            for outcome in outcomes
            for line in _failure_lines(outcome, overlay.fail_on_unattributed)
        )
        return ModelConsumerInstallResult(
            candidate_distribution=candidate.distribution,
            passed=not lines,
            outcomes=outcomes,
            elapsed_seconds=elapsed,
            budget_seconds=overlay.total_budget_seconds,
            over_budget=elapsed > overlay.total_budget_seconds,
            failure_lines=lines,
        )

    def _run(
        self, argv: Sequence[str], cwd: Path | None, timeout: float
    ) -> tuple[int, str, bool]:
        done = self._exec.handle(
            ModelCommandRequest(argv=tuple(argv), cwd=cwd, timeout_seconds=timeout)
        )
        return done.returncode, done.output, done.timed_out

    def _check_one(
        self,
        spec: ModelConsumerSpec,
        ref: str,
        request: ModelConsumerInstallRequest,
        overlay: ModelConsumerInstallOverlay,
        candidate: ModelCandidateSpec,
    ) -> ModelConsumerOutcome:
        started = time.monotonic()
        root = request.work_dir / spec.name / "src"
        venv = request.work_dir / spec.name / "venv"
        python = str(venv / "bin" / "python")
        timeout = overlay.step_timeout_seconds
        root.mkdir(parents=True, exist_ok=True)

        def failed(step: str, output: str) -> ModelConsumerOutcome:
            return ModelConsumerOutcome(
                consumer=spec.name,
                ref=ref,
                entry_points_imported=0,
                tests_collected=0,
                elapsed_seconds=time.monotonic() - started,
                setup_error=f"{step}: {output[-_TAIL_CHARS:]}",
            )

        setup = (
            ("checkout", ["git", "init", "-q", str(root)], None),
            (
                "checkout",
                ["git", "-C", str(root), "fetch", "--depth", "1", spec.repo_url, ref],
                None,
            ),
            (
                "checkout",
                ["git", "-C", str(root), "checkout", "-q", "FETCH_HEAD"],
                None,
            ),
            (
                "venv",
                ["uv", "venv", "--python", overlay.python_version, str(venv)],
                None,
            ),
            (
                "install-consumer",
                ["uv", "pip", "install", "--python", python, *spec.install_args],
                root,
            ),
            (
                "install-candidate",
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    python,
                    "--no-deps",
                    "--reinstall",
                    request.candidate_spec,
                ],
                root,
            ),
        )
        stages: dict[str, float] = {}
        for step, argv, cwd in setup:
            step_started = time.monotonic()
            code, output, timed_out = self._run(argv, cwd, timeout)
            stages[step] = stages.get(step, 0.0) + time.monotonic() - step_started
            if code != 0:
                reason = "timed out" if timed_out else f"exit {code}"
                return failed(f"{step} ({reason})", output)
        _, sha_output, _ = self._run(
            ["git", "-C", str(root), "rev-parse", "HEAD"], None, timeout
        )
        sha = sha_output.strip()

        probe_out = request.work_dir / spec.name / "probe.json"
        probe_cmd = [
            python,
            "-P",
            str(_probe_script()),
            "--distribution",
            spec.distribution,
            "--out",
            str(probe_out),
        ]
        for group in spec.entry_point_groups:
            probe_cmd += ["--group", group]
        step_started = time.monotonic()
        _, probe_output, _ = self._run(probe_cmd, root, timeout)
        stages["entry-point-import"] = time.monotonic() - step_started
        try:
            probed = json.loads(probe_out.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return failed("entry-point probe", probe_output)
        findings = [
            ModelConsumerFinding(
                consumer=spec.name,
                stage="entry-point",
                import_statement=str(item["import_statement"]),
                missing_name=str(item["missing_name"]),
                detail=f"{item['group']}:{item['name']}",
                attributed_to_candidate=_touches(
                    candidate.import_roots,
                    str(item["missing_name"]),
                    str(item["import_statement"]),
                    *(str(f) for f in item["frame_files"]),
                ),
            )
            for item in probed["failures"]
        ]

        smoke_summary = ""
        if spec.smoke_script:
            step_started = time.monotonic()
            smoke_code, smoke_output, smoke_timed_out = self._run(
                [python, "-P", str(root / spec.smoke_script)], root, timeout
            )
            smoke_findings = parse_smoke_output(
                spec.name, smoke_output, candidate.import_roots
            )
            if smoke_timed_out or (smoke_code not in (0, 1) and not smoke_findings):
                return failed("smoke script", smoke_output)
            findings.extend(smoke_findings)
            stages["smoke"] = time.monotonic() - step_started
            smoke_summary = next(
                (
                    line
                    for line in reversed(smoke_output.splitlines())
                    if line.startswith("LATEST-CORE-SMOKE packages=")
                ),
                "",
            )

        step_started = time.monotonic()
        _, collect_output, collect_timed_out = self._run(
            [
                python,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "-p",
                "no:cacheprovider",
                "-o",
                "addopts=",
                *spec.collect_args,
            ],
            root,
            timeout,
        )
        stages["collection"] = time.monotonic() - step_started
        if collect_timed_out:
            return failed("collection (timed out)", collect_output)
        collected, collection_findings = parse_collection_output(
            spec.name, collect_output, candidate.import_roots
        )
        findings.extend(collection_findings)
        return ModelConsumerOutcome(
            consumer=spec.name,
            ref=ref,
            resolved_sha=sha,
            entry_points_imported=int(probed["imported"]),
            tests_collected=collected,
            elapsed_seconds=time.monotonic() - started,
            findings=tuple(findings),
            stage_seconds=stages,
            smoke_summary=smoke_summary,
        )


def _failure_lines(
    outcome: ModelConsumerOutcome, fail_on_unattributed: bool
) -> tuple[str, ...]:
    if outcome.setup_error:
        return (
            f"{FAILURE_PREFIX}consumer={outcome.consumer} setup-failed at {outcome.setup_error}",
        )
    lines = [
        f"{FAILURE_PREFIX}{f.render()}"
        for f in outcome.findings
        if f.attributed_to_candidate or fail_on_unattributed
    ]
    if outcome.entry_points_imported == 0 and not outcome.findings:
        lines.append(
            f"{FAILURE_PREFIX}consumer={outcome.consumer} imported no entry point"
        )
    if outcome.tests_collected == 0 and not any(
        f.stage == "collection" for f in outcome.findings
    ):
        lines.append(
            f"{FAILURE_PREFIX}consumer={outcome.consumer} collected no unit test"
        )
    return tuple(lines)
