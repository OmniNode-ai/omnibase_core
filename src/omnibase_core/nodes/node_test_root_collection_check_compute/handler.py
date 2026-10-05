# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical pure conversion of infra's test-root collection guard."""

from __future__ import annotations

import tomllib
from pathlib import PurePosixPath

import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.test_root_collection_check.model_test_root_collection_check_input import (
    ModelTestRootCollectionCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_test_root_collection_check_compute.matcher_test_root_collection import (
    CI_WORKFLOW,
    FULL_SUITE_STEP_NAME,
    IGNORED_DIR_PARTS,
    SELECTOR_FILE,
    VALIDATOR_ID,
    collected_roots,
    full_suite_run_block,
    invalid_input,
    positional_pytest_args,
    workflow_runs_on_pull_request,
)


class NodeTestRootCollectionCheckCompute:
    """Validate repository configuration and discovery facts without I/O."""

    def handle(
        self, request: ModelTestRootCollectionCheckInput
    ) -> ModelValidationReport:
        """Return original violations or the diagnostic from an oracle crash."""
        sources = {file.path: file.source for file in request.files}
        findings: list[ModelValidationFinding] = []
        error_location = "pyproject.toml"
        try:
            roots = collected_roots(sources.get("pyproject.toml"), request.root_label)
            findings.extend(self._reachability(request, roots, sources))
            error_location = CI_WORKFLOW
            positionals = positional_pytest_args(
                full_suite_run_block(sources.get(CI_WORKFLOW))
            )
            if positionals:
                findings.append(
                    self._finding(
                        CI_WORKFLOW,
                        "full-suite-positional-path",
                        f"{CI_WORKFLOW} step {FULL_SUITE_STEP_NAME!r} passes positional path(s) "
                        f"{positionals} to pytest, overriding pyproject.toml testpaths. The "
                        "full suite must pass NO positional path so it inherits every collected "
                        "root (OMN-15410); use --ignore to exclude, never a positional include.",
                    )
                )
            error_location = SELECTOR_FILE
            if request.selector.error is not None:
                raise invalid_input(request.selector.error)
            mapped = set(request.selector.mapped_roots)
            declared = {root for root in roots if root != request.selector.tests_prefix}
            for root in sorted(declared - mapped):
                findings.append(
                    self._finding(
                        root,
                        "selector-unmapped-root",
                        f"{root}: collected via pyproject.toml testpaths but no "
                        "COLLOCATED_TEST_ROOTS entry in scripts/ci/detect_test_paths.py maps "
                        "any source prefix to it — a narrowed smart-selection run can never "
                        "select it (OMN-15410).",
                    )
                )
            for root in sorted(mapped - declared):
                findings.append(
                    self._finding(
                        root,
                        "selector-undeclared-root",
                        f"{root}: mapped by COLLOCATED_TEST_ROOTS in "
                        "scripts/ci/detect_test_paths.py but absent from pyproject.toml "
                        "testpaths — the selector would hand pytest a path the full suite "
                        "never collects (OMN-15410).",
                    )
                )
        except (
            ModelOnexError,
            tomllib.TOMLDecodeError,
            yaml.YAMLError,
            ValueError,
            AttributeError,
            TypeError,
        ) as exc:
            message = exc.message if isinstance(exc, ModelOnexError) else str(exc)
            findings = [
                ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity="ERROR",
                    rule_id="unparseable-input",
                    location=f"{error_location}:1",
                    message=message,
                )
            ]
        return ModelValidationReport.from_findings(
            findings=tuple(
                ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
                for finding in findings
            ),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )

    @staticmethod
    def _finding(path: str, rule: str, message: str) -> ModelValidationFinding:
        return ModelValidationFinding(
            validator_id=VALIDATOR_ID,
            severity="FAIL",
            rule_id=rule,
            location=f"{path}:1",
            message=message,
        )

    def _reachability(
        self,
        request: ModelTestRootCollectionCheckInput,
        roots: tuple[str, ...],
        sources: dict[str, str],
    ) -> list[ModelValidationFinding]:
        findings: list[ModelValidationFinding] = []
        directories = {str(PurePosixPath(path)) for path in request.directories}
        for root in roots:
            if str(PurePosixPath(root)) not in directories:
                findings.append(
                    self._finding(
                        root,
                        "missing-testpath-directory",
                        f"{root}: listed in pyproject.toml testpaths but is not a "
                        "directory on disk — pytest would abort collection with exit 5. "
                        "Remove the entry or restore the directory.",
                    )
                )
        test_dirs: set[str] = set()
        for file in request.test_files:
            for directory in PurePosixPath(file).parents:
                if directory.name == "tests" and not any(
                    part in IGNORED_DIR_PARTS for part in directory.parts
                ):
                    test_dirs.add(directory.as_posix() + "/")
        for test_dir in sorted(test_dirs):
            if any(test_dir.startswith(root) for root in roots):
                continue
            if test_dir.rstrip("/") in request.config.known_uncollected_debt:
                continue
            problem = self._standalone_problem(test_dir, request, sources)
            if problem is None:
                continue
            if problem == "unregistered":
                findings.append(
                    self._finding(
                        test_dir,
                        "uncollected-test-root",
                        f"{test_dir}: not under any pyproject.toml testpaths root "
                        f"({', '.join(roots)}), not a registered "
                        "STANDALONE_PROJECT_ROOTS entry, and not in "
                        "KNOWN_UNCOLLECTED_DEBT — no pytest invocation in CI can ever "
                        "run these tests (OMN-15378 class). Add it to testpaths (plus a "
                        "COLLOCATED_TEST_ROOTS mapping in "
                        "scripts/ci/detect_test_paths.py if it lives outside tests/), or "
                        "register it in STANDALONE_PROJECT_ROOTS with real CI wiring.",
                    )
                )
            else:
                findings.append(
                    self._finding(
                        test_dir, "standalone-project-wiring", f"{test_dir}: {problem}"
                    )
                )
        return findings

    @staticmethod
    def _standalone_problem(
        test_dir: str,
        request: ModelTestRootCollectionCheckInput,
        sources: dict[str, str],
    ) -> str | None:
        for root, workflow in request.config.standalone_projects.items():
            root_prefix = root.rstrip("/") + "/"
            if test_dir != root_prefix and not test_dir.startswith(root_prefix):
                continue
            if f"{root}/pyproject.toml" not in request.standalone_pyprojects:
                return f"registered as a STANDALONE_PROJECT_ROOTS entry but {root}/pyproject.toml does not exist"
            if workflow not in sources:
                return f"registered as a STANDALONE_PROJECT_ROOTS entry but the wiring workflow {workflow} does not exist"
            if root.rstrip("/") not in sources[workflow]:
                return (
                    "registered as a STANDALONE_PROJECT_ROOTS entry but the "
                    f"wiring workflow {workflow} never references {root} — it "
                    "cannot be running those tests"
                )
            if not workflow_runs_on_pull_request(workflow, sources):
                return (
                    "registered as a STANDALONE_PROJECT_ROOTS entry but the "
                    f"wiring workflow {workflow} never runs on a pull request "
                    "(no pull_request trigger, and no PR-reachable workflow "
                    "calls it via uses:) — the tests are invisible again"
                )
            return None
        return "unregistered"
