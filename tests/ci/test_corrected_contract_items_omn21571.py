# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-21571: corrected evidence commands reject planted regressions offline."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

import pytest
import yaml

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
VALIDATION = "src/omnibase_core/validation/"
CONTRACT = VALIDATION + "contracts/canonical_file_shape.validation.yaml"
SHAPE_CHECKER = VALIDATION + "checker_canonical_file_shape.py"
RULES = "tests/unit/nodes/node_canonical_file_shape_check_compute/test_typescript_and_shell_rules.py"
OCC_TEST = "tests/ci/test_no_occ_callers_omn20074.py"
ADMISSIBILITY_TEST = "tests/unit/handlers/test_handler_evidence_admissibility.py"
PYTEST_FLAGS = " -q -n 0 --no-cov -o addopts='' -p no:cacheprovider"


def _checks(contract_id: str, item_id: str) -> list[str]:
    contract = yaml.safe_load((ROOT / "contracts" / f"{contract_id}.yaml").read_text())
    items = [item for item in contract["dod_evidence"] if item["id"] == item_id]
    assert len(items) == 1
    values = [check["check_value"] for check in items[0]["checks"]]
    assert all(isinstance(value, str) for value in values)
    return cast(list[str], values)


def _item(contract_id: str, item_id: str) -> str:
    checks = _checks(contract_id, item_id)
    assert len(checks) == 1
    return checks[0]


def _execute(
    command: str,
    cwd: Path,
    stub_root: Path | None = None,
    extra_env: dict[str, str | None] | None = None,
) -> subprocess.CompletedProcess[str]:
    for prefix in ("env -u PYTHONPATH uv run python", "uv run python"):
        command = command.replace(prefix, shlex.quote(sys.executable))
    env = {
        "PATH": os.pathsep.join(
            [str(Path(sys.executable).parent), "/usr/local/bin", "/usr/bin", "/bin"]
        ),
        "HOME": str(cwd),
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    env["GIT_CEILING_DIRECTORIES"] = str(cwd.parent)
    for key, value in (extra_env or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    with TemporaryDirectory(prefix="omn21571-curl-") as directory:
        curl = Path(directory) / "curl"
        curl.write_text(
            f"#!{sys.executable}\n"
            "import os, re, sys\nfrom pathlib import Path\n"
            "match = re.search(r'omnibase_core/(?:[0-9a-f]*)/(.*)$', sys.argv[-1])\n"
            "if match is None: sys.exit(22)\n"
            "path = Path(os.environ['STUB_ROOT']) / match.group(1)\n"
            "if not path.is_file(): sys.exit(22)\n"
            "sys.stdout.buffer.write(path.read_bytes())\n"
        )
        curl.chmod(0o755)
        env.update(
            PATH=directory + os.pathsep + env["PATH"], STUB_ROOT=str(stub_root or cwd)
        )
        return subprocess.run(
            ["bash", "-c", command],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )


def _run(
    contract_id: str,
    item_id: str,
    cwd: Path,
    stub_root: Path | None = None,
    extra_env: dict[str, str | None] | None = None,
) -> subprocess.CompletedProcess[str]:
    if item_id == "dod-omn21520-deploy-runtimes":
        checks = [
            c for c in _checks(contract_id, item_id) if "NodeTextFileWriteEffect" in c
        ]
        assert len(checks) == 1
        return _execute(checks[0], cwd, stub_root, extra_env)
    return _execute(_item(contract_id, item_id), cwd, stub_root, extra_env)


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _copy(root: Path, relative: str) -> Path:
    return _write(root, relative, (ROOT / relative).read_text(encoding="utf-8"))


def _status(result: subprocess.CompletedProcess[str], *, passes: bool) -> None:
    assert (result.returncode == 0) == passes, result.stdout + result.stderr


FILE_CASES = [
    (
        "OMN-13703",
        "dod-topic-registry",
        (
            ("src/omnibase_core/topics.py", "PLATFORM_LOG_ENTRY", None),
            (
                "src/omnibase_core/contracts/topic_registry.yaml",
                "durability_tier: durable",
                "durability_tier: ephemeral",
            ),
        ),
    ),
    *[
        (
            "OMN-21331",
            item,
            (
                (
                    ".github/workflows/ci.yml",
                    "pytest tests/unit/nodes/node_canonical_file_shape_check_compute ",
                    "pytest tests/unit/nodes/node_other ",
                ),
                (RULES, "baselined_file_growth_any_surface", "growth"),
            ),
        )
        for item in (
            "dod-omn21331-ac2-planted-sample-refused",
            "dod-omn21331-ac3-required-context",
        )
    ],
    (
        "OMN-21514",
        "dod-omn21514-deploy-validator-source",
        (
            (CONTRACT, "validation:checker_", "validation:gone_"),
            (SHAPE_CHECKER, "def _canonical_location(", "def _gone("),
        ),
    ),
    (
        "OMN-21463",
        "dod-omn21463-deploy-source",
        (
            (
                VALIDATION + "checker_hardcoded_model_tier.py",
                "if value in tiers:",
                "if False:",
            ),
        ),
    ),
    (
        "OMN-21509",
        "dod-omn21509-deploy-published-source",
        ((CONTRACT, "validation:validator_", "validation:gone_"),),
    ),
    (
        "OMN-21520",
        "dod-omn21520-deploy-runtimes",
        (
            (
                "src/omnibase_core/nodes/node_text_file_write_effect/handler.py",
                "class NodeTextFileWriteEffect",
                "class Gone",
            ),
        ),
    ),
    (
        "OMN-16359",
        "dod-OmniNode-ai-omnibase_core-pr-1785",
        ((OCC_TEST, "def test_no_occ_callers_in_workflow_uses", "def test_gone"),),
    ),
]


@pytest.mark.parametrize(
    ("contract_id", "item_id", "mutations"), FILE_CASES, ids=[c[1] for c in FILE_CASES]
)
def test_file_probes(
    tmp_path: Path,
    contract_id: str,
    item_id: str,
    mutations: tuple[tuple[str, str, str | None], ...],
) -> None:
    if contract_id == "OMN-21520":
        assert (
            "omn-21520-bd3-node-runtimes"
            not in (ROOT / "contracts/OMN-21520.yaml").read_text()
        )
    stub_root = tmp_path / "published"
    tree = tmp_path if contract_id in {"OMN-13703", "OMN-21331"} else stub_root
    for relative, _, _ in mutations:
        _copy(tree, relative)
    _status(_run(contract_id, item_id, tmp_path, stub_root), passes=True)
    for relative, old, new in mutations:
        path = tree / relative
        original = path.read_text()
        assert old in original
        mutated = (
            original.replace(old, new)
            if new is not None
            else "\n".join(line for line in original.splitlines() if old not in line)
        )
        path.write_text(mutated)
        _status(_run(contract_id, item_id, tmp_path, stub_root), passes=False)
        path.write_text(original)


@pytest.mark.parametrize("item_id", ["dod-001"])
def test_env_fallback_runtime(tmp_path: Path, item_id: str) -> None:
    _write(tmp_path, "src/pkg/ok.py", 'import os\nx = os.environ["K"]\n')
    _status(_run("OMN-10733", item_id, tmp_path), passes=True)
    _write(
        tmp_path, "src/pkg/bad.py", 'import os\nx = os.environ.get("K", "localhost")\n'
    )
    _status(_run("OMN-10733", item_id, tmp_path), passes=False)


@pytest.mark.parametrize("item_id", ["dod-model-exists"])
def test_structured_log_fields(tmp_path: Path, item_id: str) -> None:
    _status(_run("OMN-13703", item_id, tmp_path), passes=True)
    tokens = shlex.split(_item("OMN-13703", item_id))
    source = tokens[tokens.index("-c") + 1]
    prelude = (
        "from omnibase_core.models.logging.model_structured_log_entry import ModelStructuredLogEntry\n"
        'ModelStructuredLogEntry.model_fields.pop("session_id")\n'
    )
    command = shlex.join([sys.executable, "-c", prelude + source])
    result = _execute(command, tmp_path)
    _status(result, passes=False)
    assert "AssertionError" in result.stderr


@pytest.mark.parametrize("item_id", ["dod-omn21509-delegation-join"])
def test_delegation_join(tmp_path: Path, item_id: str) -> None:
    command = _item("OMN-21509", item_id)
    assert "50ef2b21" not in (ROOT / "contracts/OMN-21509.yaml").read_text()
    _copy(tmp_path, "contracts/evidence/OMN-21509/delegation.json")
    env: dict[str, str | None] = {"GIT_CEILING_DIRECTORIES": None}
    _status(_execute("git init -q", tmp_path, extra_env=env), passes=True)
    ids = [
        "933acba5-dec5-42b3-a0f9-5c72de02bb36",
        "01a18573-a002-7f41-96e1-aa8beb32e0b8",
        "01a1851d-2df2-7f63-b61e-03cccde5216e",
    ]
    for passes, message in ((True, "\n".join(ids)), (False, "\n".join(ids[:2]))):
        commit = "git -c user.name=ContractTest -c user.email=contract@example.com -c commit.gpgsign=false commit --allow-empty -qm "
        _status(
            _execute(commit + shlex.quote(message), tmp_path, extra_env=env),
            passes=True,
        )
        sha = _execute("git rev-parse HEAD", tmp_path, extra_env=env)
        _status(sha, passes=True)
        rewritten, count = re.subn(r"\b[0-9a-f]{40}\b", sha.stdout.strip(), command)
        assert count == 3
        _status(_execute(rewritten, tmp_path, extra_env=env), passes=passes)


@pytest.mark.parametrize("item_id", ["dod-occ-diff-derived-behavior-proof-pr-1785"])
def test_occ_behavior(tmp_path: Path, item_id: str) -> None:
    command = _item("OMN-16359", item_id)
    for relative in (OCC_TEST, "tests/unit/scripts/ci/test_ci_summary_gate.py"):
        assert relative in command
        assert (ROOT / relative).is_file()
    for relative in (
        OCC_TEST,
        ".github/workflows/ci.yml",
        ".github/workflows/call-repo-evidence-gate.yml",
        ".github/required-checks.yaml",
        "scripts/ci/__init__.py",
        "scripts/ci/ci_summary_gate.py",
    ):
        _copy(tmp_path, relative)
    command = shlex.join([sys.executable, "-m", "pytest", OCC_TEST]) + PYTEST_FLAGS
    _status(_execute(command, tmp_path), passes=True)
    _write(
        tmp_path,
        ".github/workflows/ci.yml",
        "jobs:\n  planted:\n    uses: OmniNode-ai/omniclaude/.github/workflows/call-occ-companion-effect-reusable.yml@x\n",
    )
    result = _execute(command, tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "::test_no_occ_callers_in_workflow_uses" in result.stdout
    assert "1 failed" in result.stdout


@pytest.mark.parametrize("item_id", ["dod-occ-evidence-admissibility-validator"])
def test_admissibility_behavior(tmp_path: Path, item_id: str) -> None:
    tokens = shlex.split(_item("OMN-16359", item_id))
    assert tokens[:3] == ["uv", "run", "pytest"]
    assert ADMISSIBILITY_TEST in tokens
    command = shlex.join([sys.executable, "-m", *tokens[2:]]) + PYTEST_FLAGS
    _status(_execute(command, ROOT), passes=True)
    _write(
        tmp_path,
        "sitecustomize.py",
        (
            "import omnibase_core.handlers.handler_evidence_admissibility as handler\n"
            "def permissive(*args, **kwargs):\n"
            "    return handler.AdmissibilityVerdict(True, handler.EnumAdmissibilityRule.ADMISSIBLE, 'planted permissive')\n"
            "handler.classify_evidence_item = handler.classify_evidence = permissive\n"
        ),
    )
    result = _execute(
        command,
        ROOT,
        extra_env={"PYTHONPATH": os.pathsep.join([str(tmp_path), str(ROOT / "src")])},
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "planted permissive" in result.stdout
    assert "test_runner_profile_verdict" in result.stdout
