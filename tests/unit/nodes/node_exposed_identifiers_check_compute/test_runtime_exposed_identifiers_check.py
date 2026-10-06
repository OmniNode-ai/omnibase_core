# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime error modes and canonical report writes."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.models.nodes.git_file_listing.model_git_file_listing_output import (
    ModelGitFileListingOutput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_exposed_identifiers_check_compute.runtime_exposed_identifiers_check import (
    main,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

from .parity_support import SYNTHETIC, denylist_text

pytestmark = pytest.mark.unit


def arguments(tmp_path: Path) -> list[str]:
    denylist = tmp_path / "denylist.json"
    denylist.write_text(denylist_text())
    return [
        "--root",
        str(tmp_path / "root"),
        "--denylist",
        str(denylist),
        "--report-json",
        str(tmp_path / "report.json"),
    ]


def saved(tmp_path: Path) -> ModelValidationReport:
    return ModelValidationReport.model_validate_json(
        (tmp_path / "report.json").read_text()
    )


def test_empty_root_error(tmp_path: Path) -> None:
    args = arguments(tmp_path)
    (tmp_path / "root").mkdir()
    subprocess.run(
        ["git", "init", str(tmp_path / "root")],
        capture_output=True,
        check=True,
        env=scrub_git_location_env(),
    )
    assert main(args) == 1
    assert saved(tmp_path).overall_status == "ERROR"
    assert "zero files scanned" in saved(tmp_path).findings[0].message


def test_git_listing_failure_is_runtime_error(tmp_path: Path) -> None:
    args = arguments(tmp_path)
    (tmp_path / "root").mkdir()
    assert main(args) == 1
    assert saved(tmp_path).overall_status == "ERROR"
    assert "could not list repository files" in saved(tmp_path).findings[0].message


def test_default_root_from_nested_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args = arguments(tmp_path)
    root = tmp_path / "root"
    nested = root / "nested"
    nested.mkdir(parents=True)
    subprocess.run(
        ["git", "init", str(root)],
        capture_output=True,
        check=True,
        env=scrub_git_location_env(),
    )
    target = nested / "hit.txt"
    target.write_text(SYNTHETIC + "\n")
    monkeypatch.chdir(nested)
    assert main([*args[2:], "hit.txt"]) == 1
    assert saved(tmp_path).findings[0].location == "nested/hit.txt:1:1"


@pytest.mark.parametrize("document", [None, "{", "{}"])
def test_missing_or_malformed_denylist_exit_two(
    document: str | None, tmp_path: Path
) -> None:
    args = arguments(tmp_path)
    path = tmp_path / "denylist.json"
    if document is None:
        path.unlink()
    else:
        path.write_text(document)
    assert main(args) == 2
    assert saved(tmp_path).overall_status == "ERROR"


def test_denylist_required() -> None:
    assert main([]) == 2


@pytest.mark.parametrize("mode", ["blocking", "advisory"])
def test_explicit_cwd_paths_and_canonical_report(
    mode: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = arguments(tmp_path)
    root = tmp_path / "root"
    root.mkdir()
    target = root / "hit.txt"
    target.write_text(SYNTHETIC + "\n")
    monkeypatch.chdir(tmp_path)
    assert main([*args, "root/hit.txt", "--mode", mode]) == (
        1 if mode == "blocking" else 0
    )
    report = saved(tmp_path)
    assert report.overall_status == "FAIL"
    assert report.findings[0].location == "hit.txt:1:1"
    assert report.provenance.validators_run == ("arch-exposed-identifiers",)
    output = capsys.readouterr()
    assert SYNTHETIC not in output.out + output.err + report.model_dump_json()


def test_symlink_and_large_file_skipped(tmp_path: Path) -> None:
    args = arguments(tmp_path)
    root = tmp_path / "root"
    root.mkdir()
    target = root / "target.txt"
    target.write_text(SYNTHETIC)
    link = root / "link.txt"
    link.symlink_to(target)
    large = root / "large.txt"
    with large.open("wb") as stream:
        stream.write(SYNTHETIC.encode())
        stream.truncate(8 * 1024 * 1024 + 1)
    assert main([*args, str(link), str(large)]) == 0
    assert saved(tmp_path).overall_status == "PASS"


def test_missing_explicit_path_is_config_error(tmp_path: Path) -> None:
    assert main([*arguments(tmp_path), str(tmp_path / "absent.txt")]) == 2
    assert saved(tmp_path).overall_status == "ERROR"


@pytest.mark.parametrize(
    "prefix", [b"\xff" * 3000, b"\r\n" * 3000, "é".encode() * 3000]
)
@pytest.mark.parametrize("nul_offset", [8191, 8192])
def test_binary_check_uses_original_first_8192_bytes(
    prefix: bytes, nul_offset: int, tmp_path: Path
) -> None:
    args = arguments(tmp_path)
    root = tmp_path / "root"
    root.mkdir()
    target = root / "boundary.txt"
    raw = prefix + b" " * (nul_offset - len(prefix)) + b"\0\n" + SYNTHETIC.encode()
    target.write_bytes(raw)
    expected = int(nul_offset == 8192)
    assert main([*args, str(target)]) == expected
    assert len(saved(tmp_path).findings) == expected


def test_usage_error_returns_two() -> None:
    assert main(["--scope", "invalid"]) == 2


def test_excluded_only_full_tree_is_error(tmp_path: Path) -> None:
    args = arguments(tmp_path)
    root = tmp_path / "root"
    root.mkdir()
    subprocess.run(
        ["git", "init", str(root)],
        capture_output=True,
        check=True,
        env=scrub_git_location_env(),
    )
    (root / "sample.PNG").write_text(SYNTHETIC)
    assert main(args) == 1
    assert saved(tmp_path).overall_status == "ERROR"


@pytest.mark.parametrize("fallback", [False, True])
def test_empty_diff_is_clean_unless_falling_back_to_all(
    fallback: bool, tmp_path: Path
) -> None:
    args = arguments(tmp_path)
    (tmp_path / "root").mkdir()
    with patch(
        "omnibase_core.nodes.node_exposed_identifiers_check_compute.runtime_exposed_identifiers_check.NodeGitFileListingEffect.handle",
        return_value=ModelGitFileListingOutput(paths=[], fell_back_to_all=fallback),
    ):
        assert main([*args, "--scope", "diff"]) == int(fallback)
    assert saved(tmp_path).overall_status == ("ERROR" if fallback else "PASS")
