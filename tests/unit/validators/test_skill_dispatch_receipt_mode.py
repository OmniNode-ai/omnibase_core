# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for validate_skill_dispatch_receipt_mode (OMN-13098).

Covers the four checks, the ratchet allowlist semantics (tolerate listed
not-yet-migrated skills; FAIL on growth, regression, or new unreceipted
dispatch), and the CLI exit codes used by the pre-commit hook and CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums.enum_skill_receipt_rule import EnumSkillReceiptRule
from omnibase_core.validators.skill_dispatch_receipt_mode import (
    Allowlist,
    main,
    validate_skills_root,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MIGRATED_DISPATCH = """\
---
description: Dispatch shim
skill_kind: dispatch
---

# /onex:thing

```bash
onex skill thing --foo bar
```

Present the typed result fields.
"""

_METHODOLOGY = """\
---
description: A reasoning methodology
skill_kind: methodology
---

# /onex:think

Walk through the five phases. The text is the deliverable.
"""

_LEGACY_DISPATCH_NO_KIND = """\
---
description: Dispatch shim
---

# /onex:thing

```bash
uv run onex node node_thing --backend event_bus=inmemory --input "$PAYLOAD"
```

```bash
cat "$ONEX_REGISTRY_ROOT/omnimarket/.onex_state/workflow_result.json"
```
"""


def _skill(
    root: Path, name: str, *, skill_md: str, files: dict[str, str] | None = None
) -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(skill_md, encoding="utf-8")
    for rel, content in (files or {}).items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return d


def _write_allowlist(path: Path, names: list[str]) -> Path:
    lines = [
        "# OMN-13098 skill receipt-mode ratchet allowlist",
        "skills:",
    ]
    lines += [f"  - {n}" for n in names]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Check (a): explicit skill_kind
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSkillKindClassification:
    def test_missing_skill_kind_fails(self, tmp_path: Path) -> None:
        _skill(tmp_path, "thing", skill_md="---\ndescription: x\n---\n\nbody\n")
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        rules = {f.rule for f in findings}
        assert EnumSkillReceiptRule.MISSING_SKILL_KIND in rules

    def test_invalid_skill_kind_value_fails(self, tmp_path: Path) -> None:
        _skill(
            tmp_path,
            "thing",
            skill_md="---\ndescription: x\nskill_kind: bogus\n---\n\nbody\n",
        )
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert any(f.rule is EnumSkillReceiptRule.INVALID_SKILL_KIND for f in findings)

    def test_methodology_skill_passes_with_no_command(self, tmp_path: Path) -> None:
        _skill(tmp_path, "think", skill_md=_METHODOLOGY)
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert findings == []


# ---------------------------------------------------------------------------
# Check (b): bare dispatch invocation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBareDispatchInvocation:
    def test_migrated_dispatch_passes(self, tmp_path: Path) -> None:
        _skill(tmp_path, "thing", skill_md=_MIGRATED_DISPATCH)
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert findings == []

    @pytest.mark.parametrize("verb", ["run", "node", "run-node"])
    def test_bare_onex_invocation_fails(self, tmp_path: Path, verb: str) -> None:
        md = (
            "---\ndescription: x\nskill_kind: dispatch\n---\n\n"
            f"```bash\nuv run onex {verb} node_thing --input x\n```\n"
        )
        _skill(tmp_path, "thing", skill_md=md)
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert any(
            f.rule is EnumSkillReceiptRule.BARE_DISPATCH_INVOCATION for f in findings
        )

    def test_onex_skill_is_not_flagged_as_bare(self, tmp_path: Path) -> None:
        # `onex skill run-foo` must not trip the run/node/run-node matcher.
        md = (
            "---\ndescription: x\nskill_kind: dispatch\n---\n\n"
            "```bash\nonex skill run_foo --bar\n```\n"
        )
        _skill(tmp_path, "thing", skill_md=md)
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert findings == []

    def test_bare_invocation_in_prompt_md_fails(self, tmp_path: Path) -> None:
        _skill(
            tmp_path,
            "thing",
            skill_md="---\ndescription: x\nskill_kind: dispatch\n---\n\n```bash\nonex skill thing\n```\n",
            files={"prompt.md": "```bash\nuv run onex run node_thing --input x\n```\n"},
        )
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert any(
            f.rule is EnumSkillReceiptRule.BARE_DISPATCH_INVOCATION for f in findings
        )


# ---------------------------------------------------------------------------
# Check (c): no executable logic in dispatch skill dirs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoExecutableLogic:
    def test_python_file_fails(self, tmp_path: Path) -> None:
        _skill(
            tmp_path,
            "thing",
            skill_md=_MIGRATED_DISPATCH,
            files={"_lib/run.py": "print('x')\n"},
        )
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert any(
            f.rule is EnumSkillReceiptRule.EXECUTABLE_LOGIC_IN_SKILL_DIR
            for f in findings
        )

    def test_shell_script_fails(self, tmp_path: Path) -> None:
        _skill(
            tmp_path,
            "thing",
            skill_md=_MIGRATED_DISPATCH,
            files={"run.sh": "#!/bin/sh\necho x\n"},
        )
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert any(
            f.rule is EnumSkillReceiptRule.EXECUTABLE_LOGIC_IN_SKILL_DIR
            for f in findings
        )

    def test_methodology_skill_may_keep_scripts(self, tmp_path: Path) -> None:
        # Executable-logic prohibition applies only to dispatch skills.
        _skill(
            tmp_path,
            "debug",
            skill_md=_METHODOLOGY,
            files={"find-polluter.sh": "#!/bin/sh\n"},
        )
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert findings == []


# ---------------------------------------------------------------------------
# Check (d): prompt-instruction consistency
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptInstructionConsistency:
    def test_cat_workflow_result_fails(self, tmp_path: Path) -> None:
        md = (
            "---\ndescription: x\nskill_kind: dispatch\n---\n\n"
            "```bash\nonex skill thing\n```\n\n"
            "Then `cat workflow_result.json` and present it.\n"
        )
        _skill(tmp_path, "thing", skill_md=md)
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert any(
            f.rule is EnumSkillReceiptRule.PROMPT_PRINTS_RAW_JSON for f in findings
        )

    def test_surface_json_verbatim_fails(self, tmp_path: Path) -> None:
        md = (
            "---\ndescription: x\nskill_kind: dispatch\n---\n\n"
            "```bash\nonex skill thing\n```\n\n"
            "Surface the JSON verbatim to the user.\n"
        )
        _skill(tmp_path, "thing", skill_md=md)
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert any(
            f.rule is EnumSkillReceiptRule.PROMPT_PRINTS_RAW_JSON for f in findings
        )

    @pytest.mark.parametrize(
        "guidance",
        [
            "Do NOT cat workflow_result.json — receipt mode already prints it.",
            "no payload file, no cat of workflow_result.json.",
            "Never surface the JSON verbatim; present typed fields instead.",
        ],
    )
    def test_negated_raw_json_guidance_passes(
        self, tmp_path: Path, guidance: str
    ) -> None:
        # A line that PROHIBITS raw-JSON surfacing is correct guidance, not a
        # violation. This guards the delegate-frontmatter false positive.
        md = (
            "---\ndescription: x\nskill_kind: dispatch\n---\n\n"
            "```bash\nonex skill thing\n```\n\n" + guidance + "\n"
        )
        _skill(tmp_path, "thing", skill_md=md)
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert findings == []


# ---------------------------------------------------------------------------
# Ratchet allowlist semantics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRatchetAllowlist:
    def test_allowlisted_legacy_skill_tolerated(self, tmp_path: Path) -> None:
        _skill(tmp_path, "legacy", skill_md=_LEGACY_DISPATCH_NO_KIND)
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset({"legacy"}))
        )
        assert findings == []

    def test_non_allowlisted_legacy_skill_fails(self, tmp_path: Path) -> None:
        _skill(tmp_path, "legacy", skill_md=_LEGACY_DISPATCH_NO_KIND)
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert findings != []

    def test_shared_underscore_dirs_skipped(self, tmp_path: Path) -> None:
        # _lib / _shared / _bin etc. are not skills.
        _skill(tmp_path, "_lib", skill_md="not a skill")
        (tmp_path / "_shared").mkdir()
        (tmp_path / "_shared" / "helper.py").write_text("x = 1\n", encoding="utf-8")
        findings = validate_skills_root(
            tmp_path, allowlist=Allowlist(skills=frozenset())
        )
        assert findings == []


# ---------------------------------------------------------------------------
# CLI / main(): exit codes + ratchet growth/regression detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMainRatchet:
    def test_clean_root_with_empty_allowlist_exits_zero(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _skill(skills, "thing", skill_md=_MIGRATED_DISPATCH)
        al = _write_allowlist(tmp_path / "allowlist.yaml", [])
        rc = main(["--skills-root", str(skills), "--allowlist", str(al)])
        assert rc == 0

    def test_allowlisted_legacy_exits_zero(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _skill(skills, "legacy", skill_md=_LEGACY_DISPATCH_NO_KIND)
        al = _write_allowlist(tmp_path / "allowlist.yaml", ["legacy"])
        rc = main(["--skills-root", str(skills), "--allowlist", str(al)])
        assert rc == 0

    def test_new_unreceipted_dispatch_fails(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _skill(skills, "newbie", skill_md=_LEGACY_DISPATCH_NO_KIND)
        al = _write_allowlist(tmp_path / "allowlist.yaml", [])
        rc = main(["--skills-root", str(skills), "--allowlist", str(al)])
        assert rc == 1

    def test_stale_allowlist_entry_for_migrated_skill_fails(
        self, tmp_path: Path
    ) -> None:
        # Skill is migrated (clean) but still listed -> allowlist must shrink.
        skills = tmp_path / "skills"
        _skill(skills, "thing", skill_md=_MIGRATED_DISPATCH)
        al = _write_allowlist(tmp_path / "allowlist.yaml", ["thing"])
        rc = main(["--skills-root", str(skills), "--allowlist", str(al)])
        assert rc == 1

    def test_allowlist_entry_for_absent_skill_fails(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _skill(skills, "thing", skill_md=_MIGRATED_DISPATCH)
        al = _write_allowlist(tmp_path / "allowlist.yaml", ["ghost"])
        rc = main(["--skills-root", str(skills), "--allowlist", str(al)])
        assert rc == 1

    def test_missing_allowlist_is_unconditional_gate(self, tmp_path: Path) -> None:
        # When the allowlist file is deleted, the gate is unconditional.
        skills = tmp_path / "skills"
        _skill(skills, "thing", skill_md=_MIGRATED_DISPATCH)
        rc = main(
            ["--skills-root", str(skills), "--allowlist", str(tmp_path / "nope.yaml")]
        )
        assert rc == 0

    def test_missing_allowlist_fails_on_violation(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _skill(skills, "legacy", skill_md=_LEGACY_DISPATCH_NO_KIND)
        rc = main(
            ["--skills-root", str(skills), "--allowlist", str(tmp_path / "nope.yaml")]
        )
        assert rc == 1

    def test_generate_allowlist_lists_violators_only(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        skills = tmp_path / "skills"
        _skill(skills, "legacy", skill_md=_LEGACY_DISPATCH_NO_KIND)
        _skill(skills, "migrated", skill_md=_MIGRATED_DISPATCH)
        # --generate-allowlist must work WITHOUT --allowlist.
        rc = main(["--skills-root", str(skills), "--generate-allowlist"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "  - legacy" in out
        assert "  - migrated" not in out

    def test_no_allowlist_without_generate_is_usage_error(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _skill(skills, "thing", skill_md=_MIGRATED_DISPATCH)
        rc = main(["--skills-root", str(skills)])
        assert rc == 2
