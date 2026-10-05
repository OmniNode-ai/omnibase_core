# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure parsers matching the infra script's shell and workflow semantics."""

from __future__ import annotations

import ast
import re
import shlex
import tomllib
from collections.abc import Mapping
from pathlib import PurePosixPath

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.test_root_collection_check.model_test_root_collection_selector import (
    ModelTestRootCollectionSelector,
)

VALIDATOR_ID = "arch-test-root-collection"
CI_WORKFLOW = ".github/workflows/ci.yml"
SELECTOR_FILE = "scripts/ci/detect_test_paths.py"
FULL_SUITE_STEP_NAME = "Run pytest (full suite)"
IGNORED_DIR_PARTS = frozenset(
    {".git", "__pycache__", ".venv", "node_modules", ".proof-dependencies"}
)
_GH_EXPRESSION = re.compile(r"\$\{\{.*?\}\}", re.DOTALL)
_PYTEST_VALUE_OPTIONS = frozenset(
    {
        "-c",
        "-k",
        "-m",
        "-n",
        "-o",
        "-p",
        "--deselect",
        "--dist",
        "--group",
        "--ignore",
        "--junitxml",
        "--maxfail",
        "--rootdir",
        "--splits",
        "--timeout",
        "--timeout-method",
    }
)


def invalid_input(message: str) -> ModelOnexError:
    """Carry the oracle's original diagnostic without builtin error raises."""
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.VALIDATION_ERROR
    )


def collected_roots(source: str | None, root_label: str) -> tuple[str, ...]:
    """Parse testpaths exactly as the infra oracle does."""
    path = str(PurePosixPath(root_label) / "pyproject.toml")
    if source is None:
        raise invalid_input(
            f"{path} does not exist; cannot determine collected test roots"
        )
    data = tomllib.loads(source)
    paths = (
        data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("testpaths")
    )
    if not paths:
        raise invalid_input(
            f"{path} declares no [tool.pytest.ini_options] testpaths; bare "
            "`pytest` would collect the whole repository (OMN-15410)"
        )
    return tuple(str(path).rstrip("/") + "/" for path in paths)


def positional_pytest_args(run_block: str) -> list[str]:
    """Preserve the old parser, including tokens after the first command."""
    text = _GH_EXPRESSION.sub("GH_EXPR", run_block).replace("\\\n", " ")
    tokens = shlex.split(text)
    if "pytest" not in tokens:
        return []
    positionals: list[str] = []
    skip_next = False
    for token in tokens[tokens.index("pytest") + 1 :]:
        if skip_next:
            skip_next = False
            continue
        if token.startswith("-"):
            skip_next = token in _PYTEST_VALUE_OPTIONS
            continue
        positionals.append(token)
    return positionals


def workflow_mapping(source: str | None) -> Mapping[object, object]:
    """Standalone workflows fail wiring when absent or unparseable."""
    if source is None:
        return {}
    try:
        loaded: object = yaml.safe_load(source)
    except yaml.YAMLError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def workflow_runs_on_pull_request(
    workflow_rel: str, sources: Mapping[str, str], seen: frozenset[str] = frozenset()
) -> bool:
    """Check direct PR triggers or a transitive reusable-workflow caller."""
    if workflow_rel in seen:
        return False
    workflow = workflow_mapping(sources.get(workflow_rel))
    raw = workflow.get(True, workflow.get("on"))
    triggers: set[str] = set()
    if isinstance(raw, dict):
        triggers = {str(key) for key in raw}
    elif isinstance(raw, list):
        triggers = {str(item) for item in raw}
    elif isinstance(raw, str):
        triggers = {raw}
    if triggers & {"pull_request", "pull_request_target"}:
        return True
    if "workflow_call" not in triggers:
        return False
    candidates = sorted(
        path
        for path in sources
        if PurePosixPath(path).parent.as_posix() == ".github/workflows"
        and path.endswith(".yml")
    ) + sorted(
        path
        for path in sources
        if PurePosixPath(path).parent.as_posix() == ".github/workflows"
        and path.endswith(".yaml")
    )
    for candidate in candidates:
        if candidate == workflow_rel:
            continue
        jobs = workflow_mapping(sources[candidate]).get("jobs")
        if not isinstance(jobs, dict):
            continue
        calls_it = any(
            str((body or {}).get("uses") or "") == f"./{workflow_rel}"
            for body in jobs.values()
            if isinstance(body, dict)
        )
        if calls_it and workflow_runs_on_pull_request(
            candidate, sources, seen | {workflow_rel}
        ):
            return True
    return False


def full_suite_run_block(source: str | None) -> str:
    """Find the exact named full-suite step, retaining fail-closed errors."""
    if source is None:
        raise invalid_input(f"{CI_WORKFLOW} does not exist")
    workflow: object = yaml.safe_load(source)
    if not isinstance(workflow, dict):
        raise invalid_input(
            f"'{type(workflow).__name__}' object has no attribute 'get'"
        )
    jobs = workflow.get("jobs") or {}
    if not isinstance(jobs, dict):
        raise invalid_input(f"'{type(jobs).__name__}' object has no attribute 'values'")
    for job in jobs.values():
        if not isinstance(job, dict):
            raise invalid_input(f"'{type(job).__name__}' object has no attribute 'get'")
        for step in job.get("steps") or []:
            if isinstance(step, dict) and step.get("name") == FULL_SUITE_STEP_NAME:
                return str(step.get("run", ""))
    raise invalid_input(
        f"{CI_WORKFLOW} has no step named {FULL_SUITE_STEP_NAME!r}; the "
        "full-suite invocation cannot be verified (OMN-15410)"
    )


def selector_from_source(
    source: str | None, root_label: str
) -> ModelTestRootCollectionSelector:
    """Read literal selector constants without importing executable code."""
    if source is None:
        return ModelTestRootCollectionSelector(
            error="No module named 'scripts.ci.detect_test_paths'"
        )
    try:
        tree = ast.parse(source, filename="detect_test_paths.py")
    except SyntaxError as exc:
        return ModelTestRootCollectionSelector(error=str(exc))
    values: dict[str, object] = {}
    for statement in tree.body:
        value: ast.expr | None = None
        names: list[str] = []
        if isinstance(statement, ast.Assign):
            names = [
                target.id
                for target in statement.targets
                if isinstance(target, ast.Name)
            ]
            value = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(
            statement.target, ast.Name
        ):
            names = [statement.target.id]
            value = statement.value
        if value is None:
            continue
        for name in names:
            if name not in {"COLLOCATED_TEST_ROOTS", "TESTS_PREFIX"}:
                continue
            try:
                values[name] = ast.literal_eval(value)
            except (ValueError, TypeError):
                return ModelTestRootCollectionSelector(
                    error=f"{SELECTOR_FILE}: {name} must be literal typed selector configuration"
                )
    for name in ("COLLOCATED_TEST_ROOTS", "TESTS_PREFIX"):
        if name not in values:
            path = str(PurePosixPath(root_label) / SELECTOR_FILE)
            return ModelTestRootCollectionSelector(
                error=f"cannot import name '{name}' from 'scripts.ci.detect_test_paths' ({path})"
            )
    mapped, prefix = values["COLLOCATED_TEST_ROOTS"], values["TESTS_PREFIX"]
    if not isinstance(mapped, dict) or not isinstance(prefix, str):
        return ModelTestRootCollectionSelector(
            error=f"{SELECTOR_FILE}: selector constants have invalid types"
        )
    return ModelTestRootCollectionSelector(
        mapped_roots=tuple(str(root) for root in mapped.values()), tests_prefix=prefix
    )
