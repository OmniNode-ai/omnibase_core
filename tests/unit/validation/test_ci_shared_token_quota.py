# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Shared-token policy and the deployed enqueue shell use distinct credentials."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("mode", "observation"),
    [
        ("queued", "already in the merge queue"),
        ("enqueue", "VERIFIED"),
        ("behind", "update-branch issued"),
    ],
)
def test_enqueue_metadata_reads_do_not_spend_shared_token(
    tmp_path: Path, mode: str, observation: str
) -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/auto-merge.yml").read_text())
    step = next(
        s
        for s in workflow["jobs"]["auto-merge"]["steps"]
        if s.get("name") == "Enqueue armed PR and verify it entered the queue"
    )
    stub = tmp_path / "gh"
    stub.write_text("""#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
mode = os.environ['STUB_MODE']
marker = pathlib.Path(os.environ['STUB_MARKER'])
if args[:2] == ['repo', 'view']:
    assert os.environ['GH_TOKEN'] == 'run-token', 'repo metadata spent shared quota'
    print('dev')
elif args[:1] == ['api'] and 'protection/required_status_checks' in args[1]:
    assert os.environ['GH_TOKEN'] == 'shared-placeholder'
    print('true' if mode == 'behind' else 'false')
elif args[:2] == ['pr', 'update-branch']:
    assert os.environ['GH_TOKEN'] == 'shared-placeholder', 'mutation identity changed'
    marker.write_text('update')
    print('updated')
elif args[:2] == ['api', 'graphql']:
    if any('mutation(' in arg for arg in args):
        assert os.environ['GH_TOKEN'] == 'shared-placeholder', 'mutation identity changed'
        marker.write_text('enqueue')
        print('{}')
    else:
        assert os.environ['GH_TOKEN'] == 'run-token', 'PR state spent shared quota'
        if 'data.repository.pullRequest.id' in args:
            print('node-id')
        else:
            print(json.dumps({'isInMergeQueue': mode == 'queued' or marker.exists(),
                              'mergeStateStatus': 'BEHIND' if mode == 'behind' else 'CLEAN',
                              'mergeable': 'MERGEABLE', 'autoMergeRequest': {'enabledAt': 'now'}}))
else:
    raise AssertionError(args)
""")
    sleep_stub = tmp_path / "sleep"
    sleep_stub.write_text("#!/bin/sh\nexit 0\n")
    sleep_stub.chmod(0o755)
    stub.chmod(0o755)
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        cwd=ROOT,
        env={
            "PATH": f"{tmp_path}:/usr/bin:/bin",
            "GH_TOKEN": "shared-placeholder",
            "GH_READ_TOKEN": "run-token",
            "GH_REPO": "OmniNode-ai/example",
            "PR": "1",
            "STUB_MODE": mode,
            "STUB_MARKER": str(tmp_path / "mutated"),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert observation in result.stdout
    if mode != "queued":
        assert (tmp_path / "mutated").read_text() == (
            "update" if mode == "behind" else "enqueue"
        )
    assert step["env"]["GH_READ_TOKEN"] == "${{ github.token }}"


def test_unlisted_shared_secret_is_refused() -> None:
    from omnibase_core.models.validation.model_shared_token_policy_request import (
        ModelSharedTokenPolicyRequest,
    )
    from omnibase_core.nodes.node_backend_secret_discipline_compute.handler_shared_token_policy import (
        HandlerSharedTokenPolicyCompute,
    )

    result = HandlerSharedTokenPolicyCompute().handle(
        ModelSharedTokenPolicyRequest(
            workflows={
                ".github/workflows/ci.yml": "jobs:\n  check:\n    env:\n      GH_TOKEN: ${{ secrets.CROSS_REPO_PAT }}\n"
            },
            allowlist="entries: []\n",
        )
    )
    assert not result.passed
    assert result.violations[0].reference == "CROSS_REPO_PAT"


def _request(expression: str, allowlist: str = "entries: []\n"):
    from omnibase_core.models.validation.model_shared_token_policy_request import (
        ModelSharedTokenPolicyRequest,
    )

    return ModelSharedTokenPolicyRequest(
        workflows={
            ".github/workflows/ci.yml": yaml.safe_dump(
                {"jobs": {"check": {"env": {"GH_TOKEN": expression}}}}
            )
        },
        allowlist=allowlist,
    )


def _scan(expression: str, entries: list[dict[str, object]] | None = None):
    from omnibase_core.nodes.node_backend_secret_discipline_compute.handler_shared_token_policy import (
        HandlerSharedTokenPolicyCompute,
    )

    return HandlerSharedTokenPolicyCompute().handle(
        _request(expression, yaml.safe_dump({"entries": entries or []}))
    )


def _exception(**overrides: object) -> dict[str, object]:
    return {
        "workflow": ".github/workflows/ci.yml",
        "location": "/jobs/check/env/GH_TOKEN",
        "reference": "CROSS_REPO_PAT",
        "count": 1,
        "reason": "Read organization runner capacity outside this repository.",
        **overrides,
    }


@pytest.mark.parametrize(
    "expression",
    [
        "${{ secrets.CROSS_REPO_PAT }}",
        "${{ secrets['CROSS_REPO_PAT'] }}",
        "${{ SECRETS.cross_repo_pat }}",
        "${{ secrets . CROSS_REPO_PAT || github.token }}",
        "${{\nsecrets.CROSS_REPO_PAT\n}}",
        "${{ secrets.OMNI_GITHUB_TOKEN || github.token }}",
    ],
)
def test_all_shared_expression_forms_fail_without_exception(expression: str) -> None:
    result = _scan(expression)
    assert not result.passed
    assert len(result.violations) == 1


@pytest.mark.parametrize(
    "expression",
    [
        "${{ github.token }}",
        "${{ secrets.GITHUB_TOKEN }}",
        "${{ needs.detect-secrets.result }}",
        "secrets.CROSS_REPO_PAT",
    ],
)
def test_run_token_and_plain_text_do_not_spend_shared_quota(expression: str) -> None:
    result = _scan(expression)
    assert result.passed
    assert not result.uses


def test_exact_exception_is_used_and_new_location_is_refused() -> None:
    assert _scan("${{ secrets.CROSS_REPO_PAT }}", [_exception()]).passed
    result = _scan(
        "${{ secrets.CROSS_REPO_PAT }}",
        [_exception(location="/jobs/other/env/GH_TOKEN")],
    )
    assert not result.passed
    assert result.violations
    assert any("stale" in error for error in result.errors)


def test_repeat_use_requires_explicit_count() -> None:
    expression = "${{ secrets.CROSS_REPO_PAT }} ${{ secrets.CROSS_REPO_PAT }}"
    assert not _scan(expression, [_exception()]).passed
    assert _scan(expression, [_exception(count=2)]).passed


@pytest.mark.parametrize(
    "entries",
    [
        [_exception(), _exception()],
        [_exception(workflow=".github/workflows/*")],
        [_exception(reason=" ")],
        [_exception(reference="GITHUB_TOKEN")],
        [_exception(unknown="not accepted")],
    ],
)
def test_invalid_or_broad_exceptions_fail(entries: list[dict[str, object]]) -> None:
    assert not _scan("${{ secrets.CROSS_REPO_PAT }}", entries).passed


@pytest.mark.parametrize(
    "expression",
    [
        "${{ secrets[inputs.reference_name] }}",
        "${{ toJSON(secrets) }}",
        "${{ secrets[format('{0}', 'CROSS_REPO_PAT')] }}",
        "${{ secrets.CROSS_REPO_PAT || secrets[inputs.other] }}",
    ],
)
def test_indirect_secret_exports_are_refused(expression: str) -> None:
    result = _scan(expression)
    assert not result.passed
    assert any("dynamic or whole" in error for error in result.errors)


@pytest.mark.parametrize(
    "source",
    [
        "jobs: [",
        "jobs:\n  check: &loop {env: *loop}",
        "jobs: {check: {env: {GH_TOKEN: x, GH_TOKEN: y}}}",
        "jobs: {check: {<<: {env: {GH_TOKEN: x}}}}",
        "- not a workflow mapping",
    ],
)
def test_unreadable_or_ambiguous_yaml_fails_without_source_echo(source: str) -> None:
    from omnibase_core.models.validation.model_shared_token_policy_request import (
        ModelSharedTokenPolicyRequest,
    )
    from omnibase_core.nodes.node_backend_secret_discipline_compute.handler_shared_token_policy import (
        HandlerSharedTokenPolicyCompute,
    )

    result = HandlerSharedTokenPolicyCompute().handle(
        ModelSharedTokenPolicyRequest(workflows={".github/workflows/ci.yml": source})
    )
    assert not result.passed
    assert result.errors == (
        ".github/workflows/ci.yml: invalid or unsupported workflow YAML",
    )


def test_yaml_alias_expansion_cannot_reuse_another_steps_exception() -> None:
    from omnibase_core.models.validation.model_shared_token_policy_request import (
        ModelSharedTokenPolicyRequest,
    )
    from omnibase_core.nodes.node_backend_secret_discipline_compute.handler_shared_token_policy import (
        HandlerSharedTokenPolicyCompute,
    )

    source = "jobs:\n  check:\n    env: &auth\n      GH_TOKEN: ${{ secrets.CROSS_REPO_PAT }}\n  other:\n    env: *auth\n"
    result = HandlerSharedTokenPolicyCompute().handle(
        ModelSharedTokenPolicyRequest(
            workflows={".github/workflows/ci.yml": source},
            allowlist=yaml.safe_dump({"entries": [_exception()]}),
        )
    )
    assert len(result.uses) == 2
    assert len(result.violations) == 1
    assert result.violations[0].location == "/jobs/other/env/GH_TOKEN"


def test_deployed_adapter_dispatches_over_contract_topics() -> None:
    import asyncio

    from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
    from omnibase_core.nodes.node_source_file_gather_effect.runtime_shared_token_policy import (
        run_policy,
    )

    bus = EventBusInmemory()
    result = asyncio.run(run_policy(_request("${{ secrets.CROSS_REPO_PAT }}"), bus=bus))
    assert not result.passed
    contract = yaml.safe_load(
        (
            ROOT
            / "src/omnibase_core/nodes/node_backend_secret_discipline_compute/contract.yaml"
        ).read_text()
    )
    route = contract["handler_routing"]["handlers"][0]
    assert route["operation"] == "shared_token_policy"
    assert route["handler"]["name"] == "HandlerSharedTokenPolicyCompute"
    assert route["event_model"]["name"] == "ModelSharedTokenPolicyRequest"
    assert contract["name"] == "node_backend_secret_discipline_compute"
    # Positive control: both the command and result were carried by the bus.
    history = list(bus._event_history)
    assert [message.topic for message in history] == [
        *contract["event_bus"]["subscribe_topics"],
        *contract["event_bus"]["publish_topics"],
    ]


def test_cli_reads_exception_policy_and_workflows_with_no_credential(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from omnibase_core.nodes.node_source_file_gather_effect.runtime_shared_token_policy import (
        main,
    )

    directory = tmp_path / ".github/workflows"
    directory.mkdir(parents=True)
    workflow = directory / "ci.yml"
    workflow.write_text(
        _request("${{ secrets.CROSS_REPO_PAT }}").workflows[".github/workflows/ci.yml"]
    )
    assert main(["--root", str(tmp_path)]) == 1
    assert "requires a reviewed exception" in capsys.readouterr().err
    policy = (
        tmp_path
        / "src/omnibase_core/nodes/node_backend_secret_discipline_compute/contract.yaml"
    )
    policy.parent.mkdir(parents=True)
    policy.write_text(
        yaml.safe_dump({"shared_token_policy": {"entries": [_exception()]}})
    )
    assert main(["--root", str(tmp_path)]) == 0
    assert "1 reviewed uses" in capsys.readouterr().out
    workflow.write_text(
        _request("${{ github.token }}").workflows[".github/workflows/ci.yml"]
    )
    assert main(["--root", str(tmp_path)]) == 1
    assert "stale" in capsys.readouterr().err
    policy.unlink()
    assert main(["--root", str(tmp_path)]) == 0
    assert "0 reviewed uses" in capsys.readouterr().out


def test_cli_refuses_zero_workflows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from omnibase_core.nodes.node_source_file_gather_effect.runtime_shared_token_policy import (
        main,
    )

    assert main(["--root", str(tmp_path)]) == 1
    assert "no workflows" in capsys.readouterr().err


def test_ci_and_both_hook_surfaces_use_the_node() -> None:
    module = (
        "omnibase_core.nodes.node_source_file_gather_effect.runtime_shared_token_policy"
    )
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    hook = next(
        h
        for repo in config["repos"]
        for h in repo["hooks"]
        if h["id"] == "shared-token-policy"
    )
    assert module in hook["entry"]
    assert hook["pass_filenames"] is False
    exported = next(
        h
        for h in yaml.safe_load((ROOT / ".pre-commit-hooks.yaml").read_text())
        if h["id"] == "shared-token-policy"
    )
    assert module in exported["entry"]
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    job = workflow["jobs"]["backend-secret-discipline-validator"]
    assert "if" not in job and "needs" not in job
    assert any(module in step.get("run", "") for step in job["steps"])
    reusable = yaml.safe_load(
        (ROOT / ".github/workflows/shared-token-policy-reusable.yml").read_text()
    )
    assert set(reusable.get(True, reusable.get("on"))) == {"workflow_call"}
    assert reusable["permissions"] == {"contents": "read"}
    assert reusable.get(True, reusable.get("on"))["workflow_call"] is None
    assert all(
        "CROSS_REPO_PAT" not in str(step)
        for step in reusable["jobs"]["validate"]["steps"]
    )


def test_new_inherited_secret_transfer_requires_exception() -> None:
    from omnibase_core.models.validation.model_shared_token_policy_request import (
        ModelSharedTokenPolicyRequest,
    )
    from omnibase_core.nodes.node_backend_secret_discipline_compute.handler_shared_token_policy import (
        HandlerSharedTokenPolicyCompute,
    )

    source = "jobs:\n  call:\n    uses: ./.github/workflows/other.yml\n    secrets: inherit\n"
    request = ModelSharedTokenPolicyRequest(
        workflows={".github/workflows/ci.yml": source}
    )
    result = HandlerSharedTokenPolicyCompute().handle(request)
    assert not result.passed
    assert result.violations[0].reference == "SECRETS_INHERIT"
    approved = _exception(location="/jobs/call/secrets", reference="SECRETS_INHERIT")
    assert (
        HandlerSharedTokenPolicyCompute()
        .handle(
            request.model_copy(
                update={"allowlist": yaml.safe_dump({"entries": [approved]})}
            )
        )
        .passed
    )


def test_core_callers_pass_only_the_credentials_their_pinned_callee_needs() -> None:
    scanner = yaml.safe_load(
        (ROOT / ".github/workflows/call-reject-skip.yml").read_text()
    )
    assert "secrets" not in scanner["jobs"]["call-reject-skip-token"]
    ci = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    assert set(ci["jobs"]["handshake-policy-gate"]["secrets"]) == {
        "ONEXBOT_APP_ID",
        "ONEXBOT_APP_PRIVATE_KEY",
    }
    reusable = yaml.safe_load(
        (ROOT / ".github/workflows/handshake-policy-gate.yml").read_text()
    )
    assert set(reusable.get(True, reusable.get("on"))["workflow_call"]["secrets"]) == {
        "ONEXBOT_APP_ID",
        "ONEXBOT_APP_PRIVATE_KEY",
    }


@pytest.mark.parametrize(
    ("revision", "repository", "success"),
    [
        ("1" * 40, "OmniNode-ai/omnibase_core", True),
        ("dev", "OmniNode-ai/omnibase_core", False),
        ("", "OmniNode-ai/omnibase_core", False),
        ("1" * 40, "OmniNode-ai/other", False),
    ],
)
def test_reusable_uses_only_its_immutable_policy_revision(
    tmp_path: Path, revision: str, repository: str, success: bool
) -> None:
    reusable = yaml.safe_load(
        (ROOT / ".github/workflows/shared-token-policy-reusable.yml").read_text()
    )
    step = reusable["jobs"]["validate"]["steps"][0]
    output = tmp_path / "outputs"
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        env={
            "CORE_REF": revision,
            "CORE_REPOSITORY": repository,
            "GITHUB_OUTPUT": str(output),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) is success
    if success:
        assert output.read_text() == f"sha={revision}\n"
    checkout = reusable["jobs"]["validate"]["steps"][2]
    assert checkout["with"]["ref"] == "${{ steps.policy-pin.outputs.sha }}"
    assert step["env"]["CORE_REF"] == "${{ job.workflow_sha }}"


def test_repository_whole_tree_policy_is_current(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from omnibase_core.nodes.node_source_file_gather_effect.runtime_shared_token_policy import (
        main,
    )

    assert main(["--root", str(ROOT)]) == 0
    assert "5 reviewed uses" in capsys.readouterr().out
