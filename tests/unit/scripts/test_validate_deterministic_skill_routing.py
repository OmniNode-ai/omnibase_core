# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ``scripts/validate_deterministic_skill_routing.py`` (OMN-8765).

Covers the positive path (a clean skill passes) and the negative paths for
each structural violation category emitted by the CI lint gate:

- LLM SDK import in an embedded python block (``anthropic`` / ``openai``)
- ``client.messages.create`` banned LLM API call
- Subprocess orchestration call (``subprocess.run``) in a python block
- Shell wrapper around the dispatch (``bash -c 'onex run-node …'``)
- Conditional prose-fallback branch after a routing failure
- Missing dispatch declaration entirely
- Missing ``SkillRoutingError`` / ``do not produce prose`` directives

Linear ticket: OMN-8765. Parent: OMN-8737.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit

SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "validate_deterministic_skill_routing.py"
)


@pytest.fixture(scope="module")
def validator_mod() -> ModuleType:
    """Load the validator script as an importable module.

    The script defines ``@dataclass(frozen=True)`` classes which call
    ``sys.modules.get(cls.__module__).__dict__`` during class creation. We
    must register the module in ``sys.modules`` before executing it, or that
    lookup returns ``None`` and the dataclass machinery crashes.
    """
    import sys

    module_name = "validate_deterministic_skill_routing_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


# ---------------------------------------------------------------------------
# Fixtures: fixture SKILL.md content
# ---------------------------------------------------------------------------


_SKILL_ROUTING_CONTRACT = (
    "## Routing Contract\n\n"
    "Dispatch must use `onex node <node_name>`. Non-zero exit emits a "
    "`SkillRoutingError` JSON envelope — surface it directly, do not produce "
    "prose.\n"
)


def _clean_skill_md() -> str:
    return (
        "---\n"
        "description: test skill\n"
        "---\n"
        "\n"
        "# example\n\n"
        "```bash\n"
        "onex run-node node_example --arg value\n"
        "```\n\n" + _SKILL_ROUTING_CONTRACT
    )


def _skill_with_kafka_publish() -> str:
    return (
        "---\n"
        "description: kafka publish skill\n"
        "---\n"
        "\n"
        "# kafka_example\n\n"
        "This skill publishes to `onex.cmd.omnimarket.example-start.v1` and "
        "polls for the result.\n\n" + _SKILL_ROUTING_CONTRACT
    )


def _skill_with_llm_import() -> str:
    return (
        "---\n"
        "description: bad skill (llm import)\n"
        "---\n"
        "\n"
        "```bash\n"
        "onex run-node node_bad\n"
        "```\n\n"
        "```python\n"
        "import anthropic  # should be flagged\n"
        "client = anthropic.Anthropic()\n"
        "```\n\n" + _SKILL_ROUTING_CONTRACT
    )


def _skill_with_openai_from_import() -> str:
    return (
        "---\n"
        "description: openai from-import\n"
        "---\n"
        "\n"
        "```bash\n"
        "onex run-node node_bad\n"
        "```\n\n"
        "```python\n"
        "from openai import OpenAI\n"
        "client = OpenAI()\n"
        "```\n\n" + _SKILL_ROUTING_CONTRACT
    )


def _skill_with_banned_llm_call() -> str:
    return (
        "---\n"
        "description: banned llm call\n"
        "---\n"
        "\n"
        "```bash\n"
        "onex run-node node_bad\n"
        "```\n\n"
        "```python\n"
        "response = client.messages.create(model='claude', messages=[])\n"
        "```\n\n" + _SKILL_ROUTING_CONTRACT
    )


def _skill_with_subprocess_orch() -> str:
    return (
        "---\n"
        "description: subprocess orch\n"
        "---\n"
        "\n"
        "```bash\n"
        "onex run-node node_bad\n"
        "```\n\n"
        "```python\n"
        "import subprocess\n"
        "subprocess.run(['onex', 'run-node', 'x'])\n"
        "```\n\n" + _SKILL_ROUTING_CONTRACT
    )


def _skill_with_shell_wrapper() -> str:
    return (
        "---\n"
        "description: shell wrapper\n"
        "---\n"
        "\n"
        "```bash\n"
        "bash -c 'onex run-node node_bad'\n"
        "```\n\n" + _SKILL_ROUTING_CONTRACT
    )


def _skill_with_prose_fallback() -> str:
    return (
        "---\n"
        "description: prose fallback\n"
        "---\n"
        "\n"
        "```bash\n"
        "onex run-node node_bad\n"
        "if [[ $? -ne 0 ]]; then\n"
        '  echo "fallback prose when routing fails"\n'
        "fi\n"
        "```\n\n" + _SKILL_ROUTING_CONTRACT
    )


def _skill_without_dispatch() -> str:
    # Deliberately avoids the shared routing-contract block because that
    # boilerplate contains an inline-code dispatch token for documentation
    # purposes. This fixture proves the gate trips when no dispatch declaration
    # exists anywhere in the skill.
    return (
        "---\n"
        "description: no dispatch\n"
        "---\n"
        "\n"
        "# no_dispatch\n\n"
        "Some prose with no dispatch invocation whatsoever.\n\n"
        "On failure, a SkillRoutingError is emitted; do not produce prose.\n"
    )


def _skill_missing_routing_error() -> str:
    return (
        "---\n"
        "description: no routing error\n"
        "---\n"
        "\n"
        "```bash\n"
        "onex run-node node_x\n"
        "```\n\n"
        "No SkillRoutingError directive here.\n"
    )


def _skill_missing_no_prose_directive() -> str:
    return (
        "---\n"
        "description: routing error present, missing the directive\n"
        "---\n"
        "\n"
        "```bash\n"
        "onex run-node node_x\n"
        "```\n\n"
        "On failure: surface `SkillRoutingError` as the envelope.\n"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_skill(tmp_path: Path, name: str, body: str) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(body, encoding="utf-8")
    return skill_file


def _scan(
    validator_mod: ModuleType, tmp_path: Path, name: str, body: str
) -> list[object]:
    _write_skill(tmp_path, name, body)
    # Use scan_skill which returns a plain list of violations; operates on a
    # single file without requiring the enforced-skills allowlist.
    return list(validator_mod.scan_skill(tmp_path / name / "SKILL.md"))


def _violation_codes(violations: list[object]) -> set[str]:
    return {v.check for v in violations}  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Positive cases
# ---------------------------------------------------------------------------


def test_clean_skill_passes(validator_mod: ModuleType, tmp_path: Path) -> None:
    violations = _scan(validator_mod, tmp_path, "clean", _clean_skill_md())
    assert violations == [], f"clean skill should have no violations, got {violations}"


def test_kafka_publish_skill_passes(validator_mod: ModuleType, tmp_path: Path) -> None:
    violations = _scan(
        validator_mod, tmp_path, "kafka_example", _skill_with_kafka_publish()
    )
    assert violations == [], (
        "A skill whose dispatch is a Kafka publish declared in prose should "
        f"pass; got {violations}"
    )


def test_line_continuation_dispatch_counts(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    body = (
        "---\n"
        "description: line-continuation dispatch\n"
        "---\n"
        "```bash\n"
        "onex run-node node_x \\\n"
        "  --arg1 foo \\\n"
        "  --arg2 bar\n"
        "```\n\n" + _SKILL_ROUTING_CONTRACT
    )
    violations = _scan(validator_mod, tmp_path, "multiline", body)
    assert violations == [], (
        f"multi-line dispatch should count as a single dispatch; got {violations}"
    )


# ---------------------------------------------------------------------------
# Negative cases — Python block structural checks
# ---------------------------------------------------------------------------


def test_flags_anthropic_import(validator_mod: ModuleType, tmp_path: Path) -> None:
    violations = _scan(
        validator_mod, tmp_path, "bad_anthropic", _skill_with_llm_import()
    )
    codes = _violation_codes(violations)
    assert validator_mod.CHECK_LLM_IMPORT in codes


def test_flags_openai_from_import(validator_mod: ModuleType, tmp_path: Path) -> None:
    violations = _scan(
        validator_mod, tmp_path, "bad_openai", _skill_with_openai_from_import()
    )
    assert validator_mod.CHECK_LLM_IMPORT in _violation_codes(violations)


def test_flags_google_generativeai_import(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    body = (
        "---\ndescription: google gen ai\n---\n\n"
        "```bash\nonex run-node node_x\n```\n\n"
        "```python\nimport google.generativeai as genai\n```\n\n"
        + _SKILL_ROUTING_CONTRACT
    )
    violations = _scan(validator_mod, tmp_path, "bad_google", body)
    assert validator_mod.CHECK_LLM_IMPORT in _violation_codes(violations)


def test_flags_banned_llm_api_call(validator_mod: ModuleType, tmp_path: Path) -> None:
    violations = _scan(
        validator_mod, tmp_path, "bad_llm_call", _skill_with_banned_llm_call()
    )
    assert validator_mod.CHECK_LLM_API_CALL in _violation_codes(violations)


def test_flags_subprocess_orchestration(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    violations = _scan(
        validator_mod, tmp_path, "bad_subprocess", _skill_with_subprocess_orch()
    )
    assert validator_mod.CHECK_SUBPROCESS_ORCH in _violation_codes(violations)


# ---------------------------------------------------------------------------
# Negative cases — shell-block structural checks
# ---------------------------------------------------------------------------


def test_flags_shell_wrapper_around_dispatch(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    violations = _scan(
        validator_mod, tmp_path, "bad_wrapper", _skill_with_shell_wrapper()
    )
    assert validator_mod.CHECK_SHELL_WRAPPER in _violation_codes(violations)


def test_flags_prose_fallback_branch(validator_mod: ModuleType, tmp_path: Path) -> None:
    violations = _scan(
        validator_mod, tmp_path, "bad_fallback", _skill_with_prose_fallback()
    )
    assert validator_mod.CHECK_PROSE_FALLBACK in _violation_codes(violations)


def test_flags_missing_dispatch(validator_mod: ModuleType, tmp_path: Path) -> None:
    violations = _scan(
        validator_mod, tmp_path, "no_dispatch", _skill_without_dispatch()
    )
    assert validator_mod.CHECK_DISPATCH_COUNT in _violation_codes(violations)


# ---------------------------------------------------------------------------
# Negative cases — markdown contract
# ---------------------------------------------------------------------------


def test_flags_missing_skill_routing_error(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    violations = _scan(
        validator_mod,
        tmp_path,
        "missing_routing_err",
        _skill_missing_routing_error(),
    )
    assert validator_mod.CHECK_MISSING_ROUTING_ERROR in _violation_codes(violations)


def test_flags_missing_no_prose_directive(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    violations = _scan(
        validator_mod,
        tmp_path,
        "missing_no_prose",
        _skill_missing_no_prose_directive(),
    )
    assert validator_mod.CHECK_MISSING_ROUTING_ERROR in _violation_codes(violations)


# ---------------------------------------------------------------------------
# Skill-root scan & CLI entry point
# ---------------------------------------------------------------------------


def test_scan_skills_root_mixed(validator_mod: ModuleType, tmp_path: Path) -> None:
    # Install one clean Tier 1 skill and one violating Tier 1 skill at a fake root.
    tier1_names = iter(sorted(validator_mod.TIER1_DETERMINISTIC_SKILLS))
    clean_name = next(tier1_names)
    dirty_name = next(tier1_names)

    _write_skill(tmp_path, clean_name, _clean_skill_md())
    _write_skill(tmp_path, dirty_name, _skill_with_llm_import())

    result = validator_mod.scan_skills_root(tmp_path)
    # scan_skills_root walks the full allowlist; missing ones produce violations.
    assert result.skills_scanned == len(validator_mod.TIER1_DETERMINISTIC_SKILLS)
    # The clean skill must contribute zero violations; dirty must contribute ≥1.
    codes_by_skill: dict[str, set[str]] = {}
    for v in result.violations:
        codes_by_skill.setdefault(v.skill_name, set()).add(v.check)
    assert clean_name not in codes_by_skill
    assert validator_mod.CHECK_LLM_IMPORT in codes_by_skill[dirty_name]


def test_main_exit_code_on_clean_tmp_root(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    # Install all Tier 1 skills with clean content so main() exits 0.
    for name in validator_mod.TIER1_DETERMINISTIC_SKILLS:
        _write_skill(tmp_path, name, _clean_skill_md())
    exit_code = validator_mod.main(["--skills-root", str(tmp_path)])
    assert exit_code == 0


def test_main_exit_code_on_dirty_tmp_root(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    for name in validator_mod.TIER1_DETERMINISTIC_SKILLS:
        _write_skill(tmp_path, name, _skill_with_llm_import())
    exit_code = validator_mod.main(["--skills-root", str(tmp_path)])
    assert exit_code == 1


def test_main_report_mode_always_exits_zero(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    for name in validator_mod.TIER1_DETERMINISTIC_SKILLS:
        _write_skill(tmp_path, name, _skill_with_llm_import())
    exit_code = validator_mod.main(["--skills-root", str(tmp_path), "--report"])
    assert exit_code == 0


def test_main_single_skill_flag(validator_mod: ModuleType, tmp_path: Path) -> None:
    clean_name = sorted(validator_mod.TIER1_DETERMINISTIC_SKILLS)[0]
    _write_skill(tmp_path, clean_name, _clean_skill_md())
    exit_code = validator_mod.main(
        ["--skills-root", str(tmp_path), "--skill", clean_name]
    )
    assert exit_code == 0


# ---------------------------------------------------------------------------
# CodeRabbit review hardening (OMN-8765, post-merge follow-ups)
# ---------------------------------------------------------------------------


def test_flags_subprocess_orch_via_aliased_import(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    """`import subprocess as sp; sp.run(...)` must still trip the check."""
    body = (
        "---\ndescription: aliased subprocess\n---\n\n"
        "```bash\nonex run-node node_x\n```\n\n"
        "```python\n"
        "import subprocess as sp\n"
        "sp.run(['onex', 'run-node', 'x'])\n"
        "```\n\n" + _SKILL_ROUTING_CONTRACT
    )
    violations = _scan(validator_mod, tmp_path, "alias_sub", body)
    assert validator_mod.CHECK_SUBPROCESS_ORCH in _violation_codes(violations)


def test_flags_subprocess_orch_via_from_import(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    """`from subprocess import run; run(...)` must still trip the check."""
    body = (
        "---\ndescription: from-import subprocess\n---\n\n"
        "```bash\nonex run-node node_x\n```\n\n"
        "```python\n"
        "from subprocess import run\n"
        "run(['onex', 'run-node', 'x'])\n"
        "```\n\n" + _SKILL_ROUTING_CONTRACT
    )
    violations = _scan(validator_mod, tmp_path, "from_sub", body)
    assert validator_mod.CHECK_SUBPROCESS_ORCH in _violation_codes(violations)


def test_flags_os_system_via_from_import(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    """`from os import system; system(...)` must trip the subprocess-orch check."""
    body = (
        "---\ndescription: from-import os.system\n---\n\n"
        "```bash\nonex run-node node_x\n```\n\n"
        "```python\n"
        "from os import system\n"
        "system('onex run-node x')\n"
        "```\n\n" + _SKILL_ROUTING_CONTRACT
    )
    violations = _scan(validator_mod, tmp_path, "from_os", body)
    assert validator_mod.CHECK_SUBPROCESS_ORCH in _violation_codes(violations)


def test_unparseable_python_block_is_not_blocking(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    """Pseudocode in a python fence must log and skip, not emit a violation."""
    body = (
        "---\ndescription: pseudocode\n---\n\n"
        "```bash\nonex run-node node_x\n```\n\n"
        "```python\n"
        "# pseudocode, not parseable:\n"
        "if thing => other: do the stuff\n"
        "```\n\n" + _SKILL_ROUTING_CONTRACT
    )
    violations = _scan(validator_mod, tmp_path, "pseudocode", body)
    codes = _violation_codes(violations)
    assert validator_mod.CHECK_PARSE_ERROR not in codes
    assert violations == [], (
        "An unparseable python block should be skipped silently, not treated "
        f"as a violation; got {violations}"
    )


def test_placeholder_inline_dispatch_does_not_satisfy_contract(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    """Boilerplate ``onex node <node_name>`` placeholder must NOT satisfy dispatch."""
    # Deliberately strip real dispatch fences; only the routing-contract
    # placeholder sentence references ``onex node <node_name>``.
    body = (
        "---\ndescription: placeholder only\n---\n\n"
        "# placeholder_only\n\n"
        "Plain prose with no real dispatch.\n\n"
        "## Routing Contract\n\n"
        "Dispatch must use `onex node <node_name>`. Non-zero exit emits a "
        "`SkillRoutingError` JSON envelope — surface it directly, do not "
        "produce prose.\n"
    )
    violations = _scan(validator_mod, tmp_path, "placeholder_only", body)
    assert validator_mod.CHECK_DISPATCH_COUNT in _violation_codes(violations)


def test_real_inline_dispatch_satisfies_contract(
    validator_mod: ModuleType, tmp_path: Path
) -> None:
    """A concrete inline-code dispatch with a real node identifier still counts."""
    body = (
        "---\ndescription: inline concrete dispatch\n---\n\n"
        "Invoke via `onex run-node node_merge_sweep_compute` for the sweep.\n\n"
        + _SKILL_ROUTING_CONTRACT
    )
    violations = _scan(validator_mod, tmp_path, "inline_real", body)
    assert violations == [], (
        "An inline-code dispatch pointing to a real node should satisfy the "
        f"dispatch requirement; got {violations}"
    )
