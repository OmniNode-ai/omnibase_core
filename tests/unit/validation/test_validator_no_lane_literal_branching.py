# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The lane-literal branching guard (OMN-19760, runtime lane overlays plan LO16).

A runtime learns its lane and the lane's roles from a deployment overlay, so
shipped code may branch on a ROLE but never on a lane's name. The guard is a
structural AST check and carries no list of lane names: it refuses a
comparison, membership test or ``match`` of a lane-valued expression against a
string literal, and a module-level collection of lane-like literals bound to a
``*LANE*`` name. Lane ids in this file are synthetic on purpose.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omnibase_core.validation.validator_no_lane_literal_branching import (
    RULE_LANE_LITERAL_COLLECTION,
    RULE_LANE_LITERAL_COMPARE,
    RULE_LANE_LITERAL_MATCH,
    main,
    partition_against_baseline,
    scan_source,
)

pytestmark = pytest.mark.unit


def _rules(source: str) -> list[str]:
    return [v.rule for v in scan_source(source, path="pkg/mod.py")]


# --- flagged ---------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        'if lane == "lane-a":\n    pass\n',
        'if "lane-a" == lane:\n    pass\n',
        'if lane_id != "lane-b":\n    pass\n',
        'if self.runtime_lane == "lane-a":\n    pass\n',
        'if cfg.lane.value == "lane-a":\n    pass\n',
        'if lane.lower() == "lane-a":\n    pass\n',
        'if lane in ("lane-a", "lane-b"):\n    pass\n',
        'if target_lane not in {"lane-a"}:\n    pass\n',
        'import os\nif os.environ.get("ONEX_RUNTIME_LANE") == "lane-a":\n    pass\n',
        'import os\nif os.environ["ONEX_RUNTIME_LANE"] in ["lane-a"]:\n    pass\n',
        'import os\ncurrent = os.getenv("ONEX_RUNTIME_LANE", "")\n'
        'if current == "lane-a":\n    pass\n',
        'ok = lane == "lane-a"\n',
        # a name assigned from a call that yields a lane, and a copy of it
        'claimed = claimed_lane(broker)\nif claimed != "lane-a":\n    pass\n',
        'c = resolve_runtime_lane()\nd = c\nif d == "lane-a":\n    pass\n',
        # a literal moved into a module constant is still a literal
        '_TARGET: Final = "lane-a"\nif lane == _TARGET:\n    pass\n',
        '_TARGETS = ("lane-a", "lane-b")\nif lane_id in _TARGETS:\n    pass\n',
        'class C:\n    _T = "lane-a"\n\n\nif runtime_lane != _T:\n    pass\n',
    ],
)
def test_lane_compared_to_a_literal_is_flagged(source: str) -> None:
    assert _rules(source) == [RULE_LANE_LITERAL_COMPARE]


@pytest.mark.parametrize(
    "source",
    [
        'X_LANES = ("lane-a", "lane-b")\n',
        'BOUNDED_LANES: frozenset[str] = frozenset({"lane-a", "lane-b"})\n',
        'LANE_PORTS = {"lane-a": 1, "lane-b": 2}\n',
        'FAULT_LANE = ["lane-a"]\n',
        'BASE = frozenset()\nALL_LANES = BASE | frozenset({"lane-c"})\n',
        '_LANE_ALIASES: dict[str, str] = {"lane-x": "lane-a"}\n',
    ],
)
def test_module_level_lane_collection_is_flagged(source: str) -> None:
    assert _rules(source) == [RULE_LANE_LITERAL_COLLECTION]


def test_lane_membership_in_a_lane_named_collection_flags_both() -> None:
    source = 'X_LANES = ("lane-a",)\nif lane in X_LANES:\n    pass\n'
    assert sorted(_rules(source)) == [
        RULE_LANE_LITERAL_COLLECTION,
        RULE_LANE_LITERAL_COMPARE,
    ]


def test_match_on_a_lane_with_a_literal_case_is_flagged() -> None:
    source = (
        'match lane:\n    case "lane-a":\n        pass\n    case _:\n        pass\n'
    )
    assert _rules(source) == [RULE_LANE_LITERAL_MATCH]


# --- not flagged -----------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        # branching on a role is the sanctioned shape
        "if EnumRuntimeLaneRole.LAB in declaration.roles:\n    pass\n",
        'if role == "lab":\n    pass\n',
        'if lane_role == "fault_injection":\n    pass\n',
        # emptiness, identity and comparisons against other values
        'if lane == "":\n    pass\n',
        "if lane is None:\n    pass\n",
        "if lane == other_lane:\n    pass\n",
        "if lane_id in declared_lanes:\n    pass\n",
        # an env var NAME is not a lane
        'LANE_ENV_VAR = "ONEX_RUNTIME_LANE"\n',
        'LANE_ENV_KEYS = ("ONEX_RUNTIME_LANE",)\n',
        'LANE_ENV = "ONEX_RUNTIME_LANE"\nif lane == LANE_ENV:\n    pass\n',
        # a call that does not say it yields a lane
        'mode = resolve_mode()\nif mode == "lane-a":\n    pass\n',
        # a scalar constant alone is not a branch
        '_LANE_RESOURCE_PACKAGE = "pkg"\n',
        # a constant that is not a literal does not resolve
        "_T = compute()\nif lane == _T:\n    pass\n",
        # a collection not bound to a *LANE* name, and a function-local one
        'NAMES = ("lane-a", "lane-b")\n',
        # LANE as a whole name segment only, and not a path-shaped name
        '_CONTROL_PLANE_TOPICS = frozenset({"a.b.c"})\n',
        'LANES_SUBDIR = ("hooks", "lanes")\n',
        'LANE_BOUND_BACKENDS = frozenset({"backend-a"})\n',
        'def f() -> None:\n    lanes = ("lane-a",)\n',
        # an empty collection
        "KNOWN_LANES: frozenset[str] = frozenset()\n",
        # a syntax error is not this guard's finding
        "def broken(:\n",
    ],
)
def test_clean_source_passes(source: str) -> None:
    assert _rules(source) == []


# --- fingerprints and the ratchet baseline --------------------------------


def test_fingerprint_is_stable_across_line_moves() -> None:
    a = scan_source('if lane == "lane-a":\n    pass\n', path="pkg/mod.py")
    b = scan_source('\n\n\nif lane == "lane-a":\n    pass\n', path="pkg/mod.py")
    assert [v.fingerprint for v in a] == [v.fingerprint for v in b]
    assert a[0].line == 1
    assert b[0].line == 4


def test_baseline_grandfathers_old_findings_only() -> None:
    old = scan_source('X_LANES = ("lane-a",)\n', path="pkg/mod.py")
    both = scan_source(
        'X_LANES = ("lane-a",)\nif lane == "lane-b":\n    pass\n', path="pkg/mod.py"
    )
    new, grandfathered = partition_against_baseline(both, {v.fingerprint for v in old})
    assert [v.rule for v in new] == [RULE_LANE_LITERAL_COMPARE]
    assert [v.rule for v in grandfathered] == [RULE_LANE_LITERAL_COLLECTION]


def _repo(tmp_path: Path, body: str) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    (src / "mod.py").write_text(body, encoding="utf-8")
    return src / "mod.py"


def test_cli_fails_on_a_finding_and_passes_a_clean_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dirty = _repo(tmp_path, 'if lane == "lane-a":\n    pass\n')
    assert main(["--repo-root", str(tmp_path), str(dirty)]) == 1
    assert "src/mod.py:1" in capsys.readouterr().out
    dirty.write_text("if EnumRuntimeLaneRole.LAB in roles:\n    pass\n")
    assert main(["--repo-root", str(tmp_path), str(dirty)]) == 0


def test_cli_scans_a_directory(tmp_path: Path) -> None:
    _repo(tmp_path, 'X_LANES = ("lane-a",)\n')
    assert main(["--repo-root", str(tmp_path), str(tmp_path / "src")]) == 1


def test_cli_baseline_ratchets_down_and_refuses_growth(tmp_path: Path) -> None:
    dirty = _repo(tmp_path, 'X_LANES = ("lane-a",)\n')
    baseline = tmp_path / "baseline.json"
    args = ["--repo-root", str(tmp_path), "--baseline", str(baseline)]

    # seeding an absent baseline is allowed, and then the old finding passes
    assert main([*args, "--update-baseline", str(tmp_path / "src")]) == 0
    data = json.loads(baseline.read_text(encoding="utf-8"))
    assert [e["path"] for e in data["violations"]] == ["src/mod.py"]
    assert main([*args, str(dirty)]) == 0

    # a new finding fails even with the baseline in force
    dirty.write_text('X_LANES = ("lane-a",)\nif lane == "lane-b":\n    pass\n')
    assert main([*args, str(dirty)]) == 1
    # and the baseline refuses to grow to absorb it
    assert main([*args, "--update-baseline", str(tmp_path / "src")]) == 2

    # removing the finding shrinks the baseline
    dirty.write_text("VALUE = 1\n")
    assert main([*args, "--update-baseline", str(tmp_path / "src")]) == 0
    data = json.loads(baseline.read_text(encoding="utf-8"))
    assert data["violations"] == []


def test_cli_refuses_a_named_baseline_that_does_not_exist(tmp_path: Path) -> None:
    dirty = _repo(tmp_path, "VALUE = 1\n")
    missing = tmp_path / "nope.json"
    assert (
        main(["--repo-root", str(tmp_path), "--baseline", str(missing), str(dirty)])
        == 2
    )


def test_core_src_has_no_finding_outside_its_baseline() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    baseline = (
        repo_root
        / "src/omnibase_core/validation/baselines"
        / "no_lane_literal_branching_baseline.json"
    )
    assert (
        main(
            [
                "--repo-root",
                str(repo_root),
                "--baseline",
                str(baseline),
                str(repo_root / "src"),
            ]
        )
        == 0
    )
