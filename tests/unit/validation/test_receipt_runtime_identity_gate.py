# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime-identity gate over committed receipts (OMN-17308)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from omnibase_core.enums.enum_runtime_identity_rule import EnumRuntimeIdentityRule
from omnibase_core.validation.validator_receipt_runtime_identity import (
    DEFAULT_REQUIRED_PACKAGES,
    main,
    scan_receipt_file,
    scan_receipts_directory,
)


def _identity(**overrides: Any) -> dict[str, Any]:
    packages: dict[str, Any] = {
        name: {
            "name": name,
            "version": "0.0.1",
            "commit": "a" * 40,
            "source": "vcs",
        }
        for name in DEFAULT_REQUIRED_PACKAGES
    }
    base: dict[str, Any] = {
        "host": "runtime-host",
        "locus_kind": "container",
        "execution_locus": "9f2c1b0e4a55",  # pragma: allowlist secret
        "interpreter": "/app/.venv/bin/python3.12",
        "packages": packages,
        "config_source": "/app/contracts/node.yaml",
        "stamped_at": "2026-08-31T08:10:54Z",
        "schema_version": {"major": 1, "minor": 0, "patch": 0},
    }
    base.update(overrides)
    return base


def _receipt(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "skill_name": "delegate",
        "node_name": "node_delegate_skill_orchestrator",
        "status": "success",
        "correlation_id": "b9cd305c-8f31-497a-b404-b75b45b98341",
        "run_id": "0f0f0f0f-0000-4000-8000-000000000000",
        "exit_code": 0,
        "duration_ms": 12,
        "result": {"answer": "alive"},
        "result_model": "pkg.mod.ModelStub",
        "schema_version": {"major": 1, "minor": 1, "patch": 0},
        "runtime_identity": _identity(),
    }
    base.update(overrides)
    return base


def _write(tmp_path: Path, payload: object, name: str = "receipt.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.unit
class TestGatePasses:
    def test_complete_stamp_is_clean(self, tmp_path: Path) -> None:
        assert scan_receipt_file(_write(tmp_path, _receipt())) == []

    def test_grandfathered_receipt_passes_without_identity(
        self, tmp_path: Path
    ) -> None:
        """A pre-1.1.0 receipt predates the requirement and is left alone.

        The alternative -- back-filling an identity -- would invent a claim
        about a process nobody observed, which is the failure mode the gate
        exists to prevent, committed by the gate itself.
        """
        payload = _receipt(
            schema_version={"major": 1, "minor": 0, "patch": 0},
        )
        del payload["runtime_identity"]
        assert scan_receipt_file(_write(tmp_path, payload)) == []

    def test_absent_package_is_a_fact_not_a_gap(self, tmp_path: Path) -> None:
        """source 'absent' satisfies the gate; omitting the key does not."""
        identity = _identity()
        identity["packages"]["omnimarket"] = {
            "name": "omnimarket",
            "version": None,
            "commit": None,
            "source": "absent",
        }
        assert (
            scan_receipt_file(_write(tmp_path, _receipt(runtime_identity=identity)))
            == []
        )

    def test_registry_install_without_commit_is_allowed(self, tmp_path: Path) -> None:
        """A PyPI wheel genuinely has no commit; saying so is honest."""
        identity = _identity()
        identity["packages"]["omnibase_core"] = {
            "name": "omnibase_core",
            "version": "0.47.1",
            "commit": None,
            "source": "registry",
        }
        assert (
            scan_receipt_file(_write(tmp_path, _receipt(runtime_identity=identity)))
            == []
        )

    def test_non_receipt_json_is_ignored(self, tmp_path: Path) -> None:
        assert scan_receipt_file(_write(tmp_path, {"unrelated": True})) == []


@pytest.mark.unit
class TestGateFails:
    def test_missing_identity_at_current_schema(self, tmp_path: Path) -> None:
        payload = _receipt()
        del payload["runtime_identity"]
        violations = scan_receipt_file(_write(tmp_path, payload))
        assert [v.rule for v in violations] == [
            EnumRuntimeIdentityRule.MISSING_IDENTITY
        ]

    def test_required_package_omitted(self, tmp_path: Path) -> None:
        identity = _identity()
        del identity["packages"]["omnimarket"]
        violations = scan_receipt_file(
            _write(tmp_path, _receipt(runtime_identity=identity))
        )
        assert [v.rule for v in violations] == [
            EnumRuntimeIdentityRule.INCOMPLETE_IDENTITY
        ]
        assert "omnimarket" in violations[0].detail

    def test_vcs_source_without_commit(self, tmp_path: Path) -> None:
        """The OMN-17291 shape: a git claim that cannot name its content."""
        identity = _identity()
        identity["packages"]["omnimarket"]["commit"] = None
        violations = scan_receipt_file(
            _write(tmp_path, _receipt(runtime_identity=identity))
        )
        assert [v.rule for v in violations] == [
            EnumRuntimeIdentityRule.UNRESOLVED_COMMIT
        ]

    def test_shadowed_import_is_a_violation(self, tmp_path: Path) -> None:
        """Every version in the receipt names a tree that did not run.

        Reproduced live 2026-08-31 while verifying OMN-17310: a stamp taken
        under ``PYTHONPATH=<core-worktree>/src`` reported
        ``omnibase_core=0.47.1@registry`` while 0.47.2 worktree source was
        what actually executed.
        """
        identity = _identity()
        identity["packages"]["omnibase_core"].update(
            {
                "source": "shadowed",
                "commit": None,
                "import_path": "/w/OMN-17308/omnibase_core/src/omnibase_core",
            }
        )
        violations = scan_receipt_file(
            _write(tmp_path, _receipt(runtime_identity=identity))
        )
        assert [v.rule for v in violations] == [EnumRuntimeIdentityRule.SHADOWED_IMPORT]
        assert "/w/OMN-17308/omnibase_core/src/omnibase_core" in violations[0].detail

    def test_unparseable_schema_version_fails_closed(self, tmp_path: Path) -> None:
        payload = _receipt(schema_version="not-a-version")
        del payload["runtime_identity"]
        violations = scan_receipt_file(_write(tmp_path, payload))
        assert [v.rule for v in violations] == [
            EnumRuntimeIdentityRule.MALFORMED_RECEIPT
        ]

    def test_unreadable_json_fails_closed(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        violations = scan_receipt_file(path)
        assert [v.rule for v in violations] == [
            EnumRuntimeIdentityRule.MALFORMED_RECEIPT
        ]


@pytest.mark.unit
class TestCli:
    def test_directory_scan_exit_codes(self, tmp_path: Path) -> None:
        _write(tmp_path, _receipt(), name="good.json")
        assert main(["--receipts-dir", str(tmp_path)]) == 0

        bad = _receipt()
        del bad["runtime_identity"]
        _write(tmp_path, bad, name="bad.json")
        assert main(["--receipts-dir", str(tmp_path)]) == 1

    def test_explicit_files_exit_nonzero(self, tmp_path: Path) -> None:
        payload = _receipt()
        del payload["runtime_identity"]
        path = _write(tmp_path, payload)
        assert main([str(path)]) == 1

    def test_missing_directory_is_an_error(self, tmp_path: Path) -> None:
        assert main(["--receipts-dir", str(tmp_path / "nope")]) == 1

    def test_required_package_set_is_overridable(self, tmp_path: Path) -> None:
        identity = _identity()
        del identity["packages"]["omnimarket"]
        path = _write(tmp_path, _receipt(runtime_identity=identity))
        assert main([str(path)]) == 1
        assert (
            main(
                [
                    "--require-package",
                    "omnibase_core",
                    "--require-package",
                    "omnibase_infra",
                    str(path),
                ]
            )
            == 0
        )

    def test_directory_scan_is_recursive(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        bad = _receipt()
        del bad["runtime_identity"]
        _write(nested, bad, name="deep.json")
        assert len(scan_receipts_directory(tmp_path)) == 1


@pytest.mark.unit
class TestCommittedGoldens:
    """The golden receipts under docs/evidence/ must stay real receipts.

    They exist so the CI directory scan is non-vacuous. If they rot into
    non-receipts, the gate silently returns to scanning nothing while still
    reporting PASS — the OMN-14531 shape it is meant to avoid.
    """

    # Resolved from this file, never from the CWD (operating rule 6): a
    # CWD-relative fixture path is how a suite quietly stops finding its
    # fixtures and starts passing on an empty glob.
    GOLDEN_DIR = (
        Path(__file__).resolve().parents[3] / "docs" / "evidence" / "runtime-identity"
    )

    def test_goldens_are_recognised_and_clean(self) -> None:
        violations = scan_receipts_directory(self.GOLDEN_DIR)
        assert violations == []

    def test_goldens_validate_against_the_real_receipt_model(self) -> None:
        from omnibase_core.models.dispatch.model_skill_result import ModelSkillResult

        paths = sorted(self.GOLDEN_DIR.glob("*.golden.json"))
        assert len(paths) == 2
        for path in paths:
            ModelSkillResult.model_validate_json(path.read_text(encoding="utf-8"))

    def test_scan_actually_saw_two_receipts(self) -> None:
        from omnibase_core.validation.validator_receipt_runtime_identity import (
            count_receipts,
        )

        assert count_receipts(sorted(self.GOLDEN_DIR.glob("*.json"))) == 2


class TestNoTargetPathRefusesLegibly:
    """Handed no target at all, the gate refuses — it never crashes.

    Previously this branch relied on ``argparse.ArgumentParser.error()`` to
    terminate, which is true at runtime but not provable statically: CodeQL
    reported three ``py/uninitialized-local-variable`` errors on PR #1634 for
    ``candidates`` and ``target``. A validator whose own no-target path can
    raise ``UnboundLocalError`` shows the operator a traceback instead of the
    refusal it meant to give — and a traceback is much easier to wave off as
    "the tool is broken" than an explicit refusal is.

    The load-bearing assertion is that it is a REFUSAL (non-zero), never a
    pass. A gate that reports success because it was handed nothing to scan is
    the vacuous-PASS failure class (OMN-14531).
    """

    def test_no_arguments_refuses_without_raising(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main([])

        assert exit_code != 0, (
            "the gate reported success while scanning nothing — a vacuous PASS"
        )
        assert exit_code == 2
        stderr = capsys.readouterr().err
        assert "--receipts-dir" in stderr, (
            "the refusal must name how to give the gate a target"
        )
