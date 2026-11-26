# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-18595: a release cut respects the README-only documentation policy.

The release train cuts a version by merging a titled pull request. The tree it
cuts must carry no generated ``CHANGELOG.md`` (OMN-17427 keeps README.md as the
only tracked prose), and the project version must match the editable
``omnibase-core`` entry in ``uv.lock`` so the tag names the package it builds.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from omnibase_core.models.nodes.readme_only_docs.model_readme_only_docs_input import (
    ModelReadmeOnlyDocsInput,
)
from omnibase_core.nodes.node_git_file_listing_effect.handler_readme_only_docs import (
    HandlerReadmeOnlyDocs,
)
from omnibase_core.validation.checker_canonical_file_shape import (
    _count_entries,
    parse_baseline,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env
from tests.unit.nodes.node_canonical_file_shape_check_compute.support import (
    BASELINE,
    RULES,
    init_repo,
    issues,
    stage,
    write,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], env=scrub_git_location_env(), text=True
    )


def _scan(root: Path) -> tuple[str, list[str]]:
    report = HandlerReadmeOnlyDocs().handle(ModelReadmeOnlyDocsInput(root=root))
    return report.overall_status, [f.location for f in report.findings]


def test_release_tree_tracks_no_changelog() -> None:
    assert _git(REPO_ROOT, "ls-files", "--", "CHANGELOG.md").strip() == ""
    status, findings = _scan(REPO_ROOT)
    assert "CHANGELOG.md" not in findings
    assert status == "PASS", findings


def test_release_generated_changelog_is_refused(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    for name, body in (
        ("README.md", "readme\n"),
        ("CHANGELOG.md", "## v0.0.1 (2026-01-01)\n\n- release\n"),
    ):
        (tmp_path / name).write_text(body)
        _git(tmp_path, "add", "--", name)
    status, findings = _scan(tmp_path)
    assert status == "FAIL"
    assert findings == ["CHANGELOG.md"]


def test_project_version_matches_locked_editable_package() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    packages = [p for p in lock["package"] if p["name"] == "omnibase-core"]
    assert len(packages) == 1
    assert packages[0]["source"] == {"editable": "."}
    # OMN-23837: the version comes from git at build time, so neither file holds
    # one; the lock and the project still agree, each saying the version is dynamic.
    assert "version" not in project["project"]
    assert project["project"]["dynamic"] == ["version"]
    assert "version" not in packages[0]


def test_release_changelog_retains_version_0_47_50_in_root_readme() -> None:
    """Keep this cut's public notes while rejecting a standalone changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.50 (2026-10-20)" in readme
    assert "### Included Since v0.47.49" in readme
    assert (
        "- fix: cascade legs and CI Summary stop going red on a release head (#2062)"
        in readme
    )
    assert (
        "- feat: the delegation wire request admits the context_compaction task class (#2061)"
        in readme
    )


def test_release_changelog_retains_version_0_47_51_in_root_readme() -> None:
    """Keep the 0.47.51 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.51 (2026-10-20)" in readme
    assert "### Included Since v0.47.50" in readme
    assert (
        "- feat: the ticket contract item declares supersedes_ac_binding (#2067)"
        in readme
    )


def test_release_changelog_retains_version_0_47_52_in_root_readme() -> None:
    """Keep the 0.47.52 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.52 (2026-10-22)" in readme
    assert "### Included Since v0.47.51" in readme
    assert (
        "- fix: ticket contract dod_evidence items accept ac_bindings (#2076)" in readme
    )


def test_release_changelog_retains_version_0_47_53_in_root_readme() -> None:
    """Keep the 0.47.53 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.53 (2026-10-22)" in readme
    assert "### Included Since v0.47.52" in readme
    assert "- feat: the terminal cause enum gains returned_to_caller (#2081)" in readme


def test_release_changelog_retains_version_0_47_55_in_root_readme() -> None:
    """Keep the 0.47.55 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.55 (2026-10-24)" in readme
    assert "### Included Since v0.47.54" in readme
    assert (
        "- feat: every baselined file only shrinks, on every surface (#2087)" in readme
    )
    assert (
        "- feat: canonical file shape refuses TypeScript outside its locations and shell scripts everywhere (#2088)"
        in readme
    )


def test_release_changelog_retains_version_0_47_58_in_root_readme() -> None:
    """Keep the 0.47.58 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.58 (2026-10-29)" in readme
    assert "### Included Since v0.47.57" in readme
    assert (
        "- feat: the FSM executor evaluates every operator the condition model accepts (#2103)"
        in readme
    )
    assert (
        "- T4.1a: hardcoded_model_config families T (tier aliases) and N (engine names) (#2121)"
        in readme
    )


def test_release_changelog_retains_version_0_47_59_in_root_readme() -> None:
    """Keep the 0.47.59 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.59 (2026-10-30)" in readme
    assert "### Included Since v0.47.58" in readme
    assert (
        "- fix: shipped contracts name the producer of each externally produced topic (#2166)"
        in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_60_in_root_readme() -> None:
    """Keep the 0.47.60 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.60 (2026-10-31)" in readme
    assert "### Included Since v0.47.59" in readme
    assert (
        "- feat: a machine row binds the grant roles it holds by name (#2178)" in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_61_in_root_readme() -> None:
    """Keep the 0.47.61 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.61 (2026-11-01)" in readme
    assert "### Included Since v0.47.60" in readme
    assert (
        "- move the diagram-drift check into omnibase_core as a generic validator (#2216)"
        in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_62_in_root_readme() -> None:
    """Keep the 0.47.62 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.62 (2026-11-02)" in readme
    assert "### Included Since v0.47.61" in readme
    assert "- feat: add report-only merge receipt validation check (#2229)" in readme
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_66_in_root_readme() -> None:
    """Keep the 0.47.66 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.66 (2026-11-04)" in readme
    assert "### Included Since v0.47.62" in readme
    assert (
        "- fix: a ticket-cited advisory annotation is not suppression growth (#2257)"
        in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_67_in_root_readme() -> None:
    """Keep the 0.47.67 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.67 (2026-11-05)" in readme
    assert "### Included Since v0.47.66" in readme
    assert (
        "- fix: only a runner-produced PASS clears a prior FAIL supersede record (#2265)"
        in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_69_in_root_readme() -> None:
    """Keep the 0.47.69 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.69 (2026-11-07)" in readme
    assert "### Included Since v0.47.67" in readme
    assert (
        "- feat: a core validator judges each venv surface against the lock it was built from (#2274)"
        in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_70_in_root_readme() -> None:
    """Keep the 0.47.70 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.70 (2026-11-08)" in readme
    assert "### Included Since v0.47.69" in readme
    assert "- fix: the stale-pin merge bound is per sibling (#2286)" in readme
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_72_in_root_readme() -> None:
    """Keep the 0.47.72 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.72 (2026-11-10)" in readme
    assert "### Included Since v0.47.70" in readme
    assert (
        "- : Carry earlier-attempt successes in ci_summary_gate partial re-runs (#2305)"
        in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_73_in_root_readme() -> None:
    """Keep the 0.47.73 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.73 (2026-11-15)" in readme
    assert "### Included Since v0.47.72" in readme
    assert (
        "- : add generic depends-on validator for declared dependencies (#2326)"
        in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_74_in_root_readme() -> None:
    """Keep the 0.47.74 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.74 (2026-11-17)" in readme
    assert "### Included Since v0.47.73" in readme
    assert "- Remove omnibase_compat uses from omnibase_core (#2329)" in readme
    section = readme.split("## v0.47.74 (2026-11-17)")[1].split("\n## v0.47.73")[0]
    assert "\n- : " not in section, (
        "a release note line is a bare separator; the notes name no ticket (the documentation scan refuses one)"
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def _release_segment_of_wheel_built_over(tmp_path: Path, tag_after: str | None) -> str:
    """Build the package from a git history shaped like this one and read the wheel's version.

    The repository's own pyproject.toml (its hatch-vcs configuration, so any change to the version
    source is read here) is committed beside a stub package, tagged v0.47.73 and given one more commit;
    ``tag_after`` then tags that commit. Nothing reads this checkout's tags, which a shallow clone lacks.
    """
    shutil.copy(REPO_ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    (tmp_path / "README.md").write_text("stub\n", encoding="utf-8")
    (tmp_path / "src" / "omnibase_core").mkdir(parents=True)
    (tmp_path / "src" / "omnibase_core" / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    (tmp_path / "architecture-handshakes").mkdir()
    (tmp_path / "architecture-handshakes" / "gitignore-baseline.yaml").write_text(
        "stub: true\n", encoding="utf-8"
    )
    identity = ["-c", "user.name=t", "-c", "user.email=t@t"]
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, *identity, "commit", "-q", "-m", "tagged release")
    _git(tmp_path, "tag", "v0.47.73")
    (tmp_path / "README.md").write_text("stub, next\n", encoding="utf-8")
    _git(tmp_path, *identity, "commit", "-q", "-am", "the release cut")
    if tag_after is not None:
        _git(tmp_path, "tag", tag_after)
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path / "dist")],
        cwd=tmp_path,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
        text=True,
    )
    (wheel,) = (tmp_path / "dist").glob("omnibase_core-*.whl")
    match = re.match(r"omnibase_core-(?P<version>[^-]+)-", wheel.name)
    assert match is not None, wheel.name
    return match.group("version")


def test_release_derived_version_reads_0_47_74_over_the_v0_47_73_tag(
    tmp_path: Path,
) -> None:
    """The version comes from git: the commit after v0.47.73 builds as the 0.47.74 development line."""
    derived = _release_segment_of_wheel_built_over(tmp_path, tag_after=None)
    assert re.fullmatch(r"0\.47\.74\.dev1\+g[0-9a-f]+", derived), derived


def test_release_derived_version_reads_exactly_0_47_74_once_tagged(
    tmp_path: Path,
) -> None:
    assert (
        _release_segment_of_wheel_built_over(tmp_path, tag_after="v0.47.74")
        == "0.47.74"
    )


_VALIDATOR_CODE_LINE_LIMIT = 731
_VALIDATOR = "src/omnibase_core/validation/validator_canonical_file_shape.py"
_RATCHET_RULES = {"baselined-file-growth", "baseline-stale", "baseline-growth"}


def _baseline_entries(text: str) -> list[str]:
    """The paths of a baseline file, as the ratchet parses them."""
    return parse_baseline(text)


def test_file_shape_baseline_validator_holds_at_most_731_code_lines() -> None:
    """The count is the ratchet's own (``_count_entries`` with the contract's comment prefixes)."""
    validator = (REPO_ROOT / _VALIDATOR).read_text(encoding="utf-8")
    assert (
        _count_entries(validator, RULES.parameters.comment_prefixes)
        <= _VALIDATOR_CODE_LINE_LIMIT
    )


def test_file_shape_baseline_ratchet_refuses_a_validator_of_732_code_lines(
    tmp_path: Path,
) -> None:
    """Negative control, through the real ratchet: one more code line in a baselined file is refused."""
    path = "scripts/legacy_tool.py"
    body = "".join(f"x{i} = {i}\n" for i in range(_VALIDATOR_CODE_LINE_LIMIT))
    write(tmp_path, path, body)
    init_repo(tmp_path, baselined=[path])
    write(tmp_path, path, body + "x_extra = 1\n")
    stage(tmp_path)
    found = issues(tmp_path)
    assert [i.code for i in found] == ["baselined-file-growth"]
    assert f"{_VALIDATOR_CODE_LINE_LIMIT} -> {_VALIDATOR_CODE_LINE_LIMIT + 1}" in (
        found[0].message
    )


def test_file_shape_baseline_ratchet_counts_code_lines_not_comments_or_blanks(
    tmp_path: Path,
) -> None:
    """Positive control: comment and blank lines added to a baselined file are not growth."""
    path = "scripts/legacy_tool.py"
    write(tmp_path, path, "a = 1\n")
    init_repo(tmp_path, baselined=[path])
    write(tmp_path, path, "# note\n\na = 1\n# another\n")
    stage(tmp_path)
    assert issues(tmp_path) == ()


def test_file_shape_baseline_ratchet_refuses_an_entry_that_names_no_file(
    tmp_path: Path,
) -> None:
    write(tmp_path, "README.md", "x\n")
    init_repo(tmp_path, baselined=["scripts/gone.py"])
    assert {i.code for i in issues(tmp_path)} == {"baseline-stale"}


def test_file_shape_baseline_of_this_tree_passes_the_real_ratchet() -> None:
    """The ratchet itself, over this checkout at HEAD against its merge base with the landing ref.

    Where the landing ref is absent (a shallow checkout) the base is HEAD, so the baseline-shape rules
    still read the whole tree; where it is present they read the growth of this release too.
    """
    refused = [i for i in issues(REPO_ROOT, head="HEAD") if i.code in _RATCHET_RULES]
    assert refused == [], [f"{i.code}: {i.file_path}: {i.message}" for i in refused]


def test_file_shape_baseline_names_no_file_this_release_adds() -> None:
    """The baseline only shrinks: every entry names a file this tree tracks."""
    baseline = REPO_ROOT / BASELINE
    entries = _baseline_entries(baseline.read_text(encoding="utf-8"))
    assert entries, "the baseline holds the files that predate the rule"
    assert len(entries) == len(set(entries))
    tracked = set(_git(REPO_ROOT, "ls-files").splitlines())
    missing = [entry for entry in entries if entry not in tracked]
    assert missing == [], f"baseline entries naming no tracked file: {missing}"


def test_file_shape_baseline_entry_naming_a_missing_file_fails_this_check(
    tmp_path: Path,
) -> None:
    """Negative control for the existence check above, on a repository whose entry names no file."""
    write(tmp_path, "README.md", "x\n")
    init_repo(tmp_path, baselined=["scripts/gone.py"])
    tracked = set(_git(tmp_path, "ls-files").splitlines())
    entries = _baseline_entries((tmp_path / BASELINE).read_text(encoding="utf-8"))
    assert [e for e in entries if e not in tracked] == ["scripts/gone.py"]


def test_release_changelog_restored_on_the_real_tree_is_refused(
    tmp_path: Path,
) -> None:
    """AC1 falsifier: this release tree passes; the same tree with CHANGELOG.md restored fails the validator."""
    clone = tmp_path / "tree"
    _git(tmp_path, "clone", "-q", "--shared", str(REPO_ROOT), str(clone))
    assert _scan(clone) == ("PASS", [])
    (clone / "CHANGELOG.md").write_text("## v0.0.1 (2026-01-01)\n\n- release\n")
    _git(clone, "add", "--", "CHANGELOG.md")
    status, findings = _scan(clone)
    assert status == "FAIL"
    assert "CHANGELOG.md" in findings


def test_release_readme_states_the_behaviour_changes_of_the_release_branch() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("### Behaviour changes on this release branch")[1].split(
        "\n## "
    )[0]
    notes = [line for line in section.splitlines() if line.startswith("- ")]
    assert len(notes) == 7, notes
    assert "uv.lock" in readme.split("### Included Since v0.47.73")[0]


def test_release_derived_version_real_history_reads_a_tag_no_newer_than_the_readme_release() -> (
    None
):
    """The version command of pyproject.toml, run on this checkout's own history (no synthetic tags).

    A checkout with tags reads ``v<tag>-<n>-g<sha>``, and a reachable tag newer than the release at the
    top of README would mean the notes lag the history. How many recent tags a clone holds varies, so the
    check is an upper bound, not an equality. A shallow checkout carries no tags and the command fails
    there; that is asserted, so the test never skips.
    """
    options = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text("utf-8"))["tool"][
        "hatch"
    ]["version"]["raw-options"]
    described = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *options["git_describe_command"][1:]],
        env=scrub_git_location_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    if described.returncode != 0:
        shallow = _git(REPO_ROOT, "rev-parse", "--is-shallow-repository").strip()
        assert shallow == "true", described.stderr
        return
    match = re.match(r"v(?P<tag>\d+\.\d+\.\d+)-\d+-g[0-9a-f]+", described.stdout)
    assert match is not None, described.stdout
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    top = re.search(r"^## v(\d+\.\d+\.\d+) ", readme, re.MULTILINE)
    assert top is not None

    def _key(version: str) -> tuple[int, ...]:
        return tuple(int(part) for part in version.split("."))

    assert _key(match.group("tag")) <= _key(top.group(1)), (
        described.stdout,
        top.group(1),
    )


def test_release_changelog_retains_version_0_47_75_in_root_readme() -> None:
    """Keep the 0.47.75 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.75 (2026-11-19)" in readme
    assert "### Included Since v0.47.74" in readme
    assert (
        "- : move the dev-tag lineage and effect-backends nodes out of omnibase_core (#2312)"
        in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_76_in_root_readme() -> None:
    """Keep the 0.47.76 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.76 (2026-11-20)" in readme
    assert "### Included Since v0.47.75" in readme
    assert (
        "- fix: first_party_ref pairs hook rev and CI tag as one home (#2347)" in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_77_in_root_readme() -> None:
    """Keep the 0.47.77 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.77 (2026-11-23)" in readme
    assert "### Included Since v0.47.76" in readme
    assert (
        "- fix: resolve YAML merge keys in the precommit interpreter matcher independent of pyyaml version (#2358)"
        in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_78_in_root_readme() -> None:
    """Keep the 0.47.78 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.78 (2026-11-24)" in readme
    assert "### Included Since v0.47.77" in readme
    assert (
        "- : the ledger render reads through the bus-backed ledger client (#2360)"
        in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_79_in_root_readme() -> None:
    """Keep the 0.47.79 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.79 (2026-11-25)" in readme
    assert "### Included Since v0.47.78" in readme
    assert (
        "- : extend hook-rev exemption for 1c9566e2c249 to 2026-12-04 (#2367)" in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_80_in_root_readme() -> None:
    """Keep the 0.47.80 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.80 (2026-11-25)" in readme
    assert "### Included Since v0.47.79" in readme
    assert (
        "- : CI Summary poll counts a concluded job as done, pages 30 then 10, stall bound (#2371)"
        in readme
    )
    assert not (REPO_ROOT / "CHANGELOG.md").exists()


def test_release_changelog_retains_version_0_47_81_in_root_readme() -> None:
    """Keep the 0.47.81 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.81 (2026-11-26)" in readme
    assert "### Included Since v0.47.80" in readme
    assert "- : delegation terminal carries provider_generation_id (#2379)" in readme
    assert not (REPO_ROOT / "CHANGELOG.md").exists()
