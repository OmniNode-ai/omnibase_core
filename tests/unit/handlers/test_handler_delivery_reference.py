# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Acceptance coverage for the pure delivery reference checker."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_delivery_path_role import EnumDeliveryPathRole as Role
from omnibase_core.enums.enum_delivery_reference_kind import (
    EnumDeliveryReferenceKind as Kind,
)
from omnibase_core.enums.enum_delivery_resolved_kind import (
    EnumDeliveryResolvedKind as Resolved,
)
from omnibase_core.enums.enum_delivery_status import EnumDeliveryStatus as Status
from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.handlers.handler_delivery_reference import (
    check_delivery_paths,
    classify_reference,
    discover_references,
    judge_reference,
    reconcile_consumers,
    to_validation_issues,
)
from omnibase_core.models.delivery import (
    ModelDeliveryDependencyMechanism,
    ModelDeliveryDiscoveryPattern,
    ModelDeliveryFacts,
    ModelDeliveryFile,
    ModelDeliveryOverlay,
    ModelDeliveryPath,
    ModelDeliveryRef,
    ModelDeliveryRolePermission,
)

pytestmark = pytest.mark.unit

TAG = "dev-20261028010203-abcdef012345"
CANDIDATE = "cand-123-abcdef012345"
SHA = "a" * 40


def overlay(
    *, tag_pattern: str = r"dev-\d{14}-[0-9a-f]{12}", mechanisms: bool = True
) -> ModelDeliveryOverlay:
    """Keep all delivery policy in fixture data."""
    return ModelDeliveryOverlay(
        tag_pattern=tag_pattern,
        candidate_tag_pattern=r"cand-\d+-[0-9a-f]{12}",
        bump_automation_patterns=(r"^bump/", r"version-bump\.yml"),
        dependency_mechanisms=tuple(
            ModelDeliveryDependencyMechanism(
                mechanism_name=name,
                pattern=f"^bump/{name}$",
                ruling=f"fixture_ruling_{name}",
            )
            for name in (
                "consumer_test_pin",
                "validator_requirements_spec",
                "package_floor",
            )
        )
        if mechanisms
        else (),
        role_permissions=tuple(
            ModelDeliveryRolePermission(role=role, kinds=(kind,))
            for role, kind in (
                (Role.CONTINUOUS, Kind.DEV_MERGE_TAG),
                (Role.PRE_PR, Kind.CANDIDATE_TAG),
                (Role.REQUIRED_GATE, Kind.GATE_BOOTSTRAP_PIN),
                (Role.DEPENDENCY, Kind.DECLARED_DEPENDENCY_PIN),
            )
        ),
        consumer_kinds=(
            "marketplace_entry",
            "cache_key",
            "install_specifier",
            "uses_line",
            "pin_file_entry",
        ),
        reusable_workflow_consumer_kinds=("uses_line",),
        discovery_patterns=(
            ModelDeliveryDiscoveryPattern(
                consumer_kind="uses_line",
                file_pattern="*.yml",
                reference_pattern=r"uses: \S+@(?P<ref>\S+)",
            ),
            ModelDeliveryDiscoveryPattern(
                consumer_kind="marketplace_entry",
                file_pattern="*.txt",
                reference_pattern=r"entry=(?P<ref>\S+)",
            ),
        ),
    )


def path(
    role: Role = Role.CONTINUOUS, consumer: str = "marketplace_entry"
) -> ModelDeliveryPath:
    return ModelDeliveryPath(
        path_name="artifact",
        producing_repository="fixture-producer",
        consumer_kind=consumer,
        location="consumer.yml",
        role=role,
        bootstrap_pin=SHA if role == Role.REQUIRED_GATE else None,
    )


def ref(
    text: str = TAG,
    resolved: Resolved = Resolved.TAG,
    consumer: str = "marketplace_entry",
    **changes: object,
) -> ModelDeliveryRef:
    data: dict[str, object] = {
        "path_name": "artifact",
        "location": "consumer.yml",
        "consumer_kind": consumer,
        "reference_text": text,
        "resolved_kind": resolved,
    }
    data.update(changes)
    return ModelDeliveryRef.model_validate(data)


@pytest.mark.parametrize(
    ("text", "resolved", "consumer", "role", "changes", "kind", "allowed"),
    [
        (
            "main",
            Resolved.BRANCH,
            "marketplace_entry",
            Role.CONTINUOUS,
            {},
            Kind.BRANCH,
            False,
        ),
        (
            "1.2.3",
            Resolved.VERSION,
            "cache_key",
            Role.CONTINUOUS,
            {},
            Kind.HAND_KEPT_VERSION,
            False,
        ),
        (
            SHA,
            Resolved.COMMIT,
            "install_specifier",
            Role.CONTINUOUS,
            {},
            Kind.SHA,
            False,
        ),
        ("main", Resolved.BRANCH, "uses_line", Role.CONTINUOUS, {}, Kind.BRANCH, False),
        (
            "bump/release",
            Resolved.BRANCH,
            "pin_file_entry",
            Role.CONTINUOUS,
            {},
            Kind.BUMP_PR,
            False,
        ),
        (
            TAG,
            Resolved.TAG,
            "marketplace_entry",
            Role.CONTINUOUS,
            {},
            Kind.DEV_MERGE_TAG,
            True,
        ),
        (
            CANDIDATE,
            Resolved.TAG,
            "install_specifier",
            Role.PRE_PR,
            {
                "candidate_pr_head": SHA,
                "candidate_test_merge_target": "b" * 40,
                "candidate_artifact_digest": "digest",
            },
            Kind.CANDIDATE_TAG,
            True,
        ),
        (
            CANDIDATE,
            Resolved.TAG,
            "install_specifier",
            Role.CONTINUOUS,
            {
                "candidate_pr_head": SHA,
                "candidate_test_merge_target": "b" * 40,
                "candidate_artifact_digest": "digest",
            },
            Kind.CANDIDATE_TAG,
            False,
        ),
        (
            SHA,
            Resolved.COMMIT,
            "pin_file_entry",
            Role.REQUIRED_GATE,
            {"runtime_resolution": True},
            Kind.GATE_BOOTSTRAP_PIN,
            True,
        ),
    ],
    ids=[
        "marketplace_branch",
        "version_cache",
        "sha_install",
        "workflow_branch",
        "bump_branch",
        "continuous_tag",
        "bound_candidate",
        "candidate_wrong_role",
        "runtime_bootstrap",
    ],
)
def test_ac1_real_forms(
    text: str,
    resolved: Resolved,
    consumer: str,
    role: Role,
    changes: dict[str, object],
    kind: Kind,
    allowed: bool,
) -> None:
    issue = judge_reference(
        ref(text, resolved, consumer, **changes), path(role, consumer), overlay()
    )
    assert (issue.kind, issue.reference_allowed) == (kind, allowed)
    assert issue.status == (Status.ALLOWED if allowed else Status.REFUSED)


@pytest.mark.parametrize(
    "missing",
    ["candidate_pr_head", "candidate_test_merge_target", "candidate_artifact_digest"],
)
@pytest.mark.parametrize("empty", [None, ""])
def test_ac1_candidate_requires_complete_binding(
    missing: str, empty: str | None
) -> None:
    binding = {
        "candidate_pr_head": SHA,
        "candidate_test_merge_target": SHA,
        "candidate_artifact_digest": "digest",
    }
    binding[missing] = empty
    assert (
        judge_reference(ref(CANDIDATE, **binding), path(Role.PRE_PR), overlay()).reason
        == "candidate_not_bound"
    )


def test_ac2_unknown_refused_and_unknown_permission_rejected() -> None:
    issue = judge_reference(ref("unrecognized", Resolved.UNRESOLVED), path(), overlay())
    assert issue.kind == Kind.UNKNOWN and not issue.reference_allowed
    data = overlay().model_dump()
    data["role_permissions"] = [{"role": "continuous", "kinds": ["unknown"]}]
    with pytest.raises(ValidationError, match=r"UNKNOWN|unknown"):
        ModelDeliveryOverlay.model_validate(data)


def test_ac3_branch_named_like_tag_is_branch() -> None:
    assert (
        judge_reference(ref(TAG, Resolved.BRANCH), path(), overlay()).kind
        == Kind.BRANCH
    )


def test_ac4_bump_workflow_overrides_valid_tag() -> None:
    issue = judge_reference(
        ref(automation_names=(".github/workflows/version-bump.yml",)), path(), overlay()
    )
    assert issue.kind == Kind.BUMP_PR and not issue.reference_allowed


@pytest.mark.parametrize(
    "mechanism", ["consumer_test_pin", "validator_requirements_spec", "package_floor"]
)
def test_ac4_dependency_mechanisms_require_declaration_and_role(mechanism: str) -> None:
    observed = ref(f"bump/{mechanism}", Resolved.BRANCH)
    declared = judge_reference(observed, path(Role.DEPENDENCY), overlay())
    assert declared.kind == Kind.DECLARED_DEPENDENCY_PIN and declared.reference_allowed
    assert not judge_reference(observed, path(), overlay()).reference_allowed
    absent = judge_reference(observed, path(Role.DEPENDENCY), overlay(mechanisms=False))
    assert absent.kind == Kind.BUMP_PR and not absent.reference_allowed


def test_ac5_literal_workflow_tag_and_sha_are_refused() -> None:
    issue = judge_reference(
        ref(consumer="uses_line"), path(consumer="uses_line"), overlay()
    )
    assert issue.kind == Kind.HAND_KEPT_VERSION and not issue.reference_allowed
    assert judge_reference(
        ref(consumer="uses_line", runtime_resolution=True),
        path(consumer="uses_line"),
        overlay(),
    ).reference_allowed
    issue = judge_reference(
        ref(SHA, Resolved.COMMIT),
        path(Role.REQUIRED_GATE).model_copy(update={"bootstrap_pin": None}),
        overlay(),
    )
    assert issue.kind == Kind.SHA and not issue.reference_allowed


def test_ac5_bootstrap_requires_runtime_resolution() -> None:
    assert (
        judge_reference(
            ref(SHA, Resolved.COMMIT), path(Role.REQUIRED_GATE), overlay()
        ).reason
        == "bootstrap_without_runtime_resolution"
    )
    assert judge_reference(
        ref(SHA, Resolved.COMMIT, runtime_resolution=True),
        path(Role.REQUIRED_GATE),
        overlay(),
    ).reference_allowed


def test_ac6_reconcile_blocks_unreadable_then_sorts_undeclared() -> None:
    facts = ModelDeliveryFacts(
        overlay=overlay(),
        paths=(path(),),
        unreadable_locations=("consumer.yml",),
        discovered=(
            ref("z", Resolved.BRANCH, location="z.yml"),
            ref("b", Resolved.BRANCH, location="a.yml", line_number=2),
            ref("a", Resolved.BRANCH, location="a.yml", line_number=1),
            ref(),
        ),
    )
    issues = reconcile_consumers(facts)
    assert [i.reason for i in issues] == ["declaration_unreadable"] + [
        "consumer_not_declared"
    ] * 3
    assert [i.location for i in issues] == ["consumer.yml", "a.yml", "a.yml", "z.yml"]
    assert issues[1].kind == Kind.BRANCH and issues[1].status == Status.UNDECLARED
    assert all(not i.reference_allowed for i in issues)


def test_ac6_discovery_multiple_files_matches_and_unlisted_consumer_end_to_end() -> (
    None
):
    configured = overlay()
    files = (
        ModelDeliveryFile(
            location="extra.yml",
            text="heading\nuses: producer@main uses: producer@other\n",
        ),
        ModelDeliveryFile(location="market.txt", text="entry=main\nentry=next"),
    )
    found = discover_references(files, configured)
    assert [(r.location, r.line_number, r.reference_text) for r in found] == [
        ("extra.yml", 2, "main"),
        ("extra.yml", 2, "other"),
        ("market.txt", 1, "main"),
        ("market.txt", 2, "next"),
    ]
    assert all(
        r.path_name is None and r.resolved_kind == Resolved.UNRESOLVED for r in found
    )
    data = configured.model_dump()
    data["consumer_kinds"] = ["pin_file_entry"]
    unlisted = ModelDeliveryOverlay.model_validate(data)
    issues = reconcile_consumers(
        ModelDeliveryFacts(
            overlay=unlisted, paths=(), discovered=discover_references(files, unlisted)
        )
    )
    assert len(issues) == 4 and all(i.status == Status.UNDECLARED for i in issues)
    assert not discover_references(
        (ModelDeliveryFile(location="skip.json", text="entry=main"),), configured
    )


@pytest.mark.parametrize(
    ("text", "role"), [(TAG, Role.CONTINUOUS), (CANDIDATE, Role.PRE_PR)]
)
def test_ac7_tag_retarget_is_refused_before_role_or_binding(
    text: str, role: Role
) -> None:
    moved = ref(
        text,
        first_resolved_target=SHA,
        resolved_target="b" * 40,
        candidate_pr_head=SHA,
        candidate_test_merge_target=SHA,
        candidate_artifact_digest="digest",
    )
    issue = judge_reference(moved, path(role), overlay())
    assert (issue.status, issue.reason, issue.reference_allowed) == (
        Status.TAG_MOVED,
        "tag_target_changed",
        False,
    )
    assert judge_reference(
        moved.model_copy(update={"resolved_target": SHA}), path(role), overlay()
    ).reference_allowed


def test_ac8_tag_policy_is_overlay_data() -> None:
    observed = ref("release-123")
    assert not judge_reference(observed, path(), overlay()).reference_allowed
    assert judge_reference(
        observed, path(), overlay(tag_pattern=r"release-\d+")
    ).reference_allowed


def test_ac8_ac9_sources_hold_no_policy_or_protocol_dependency() -> None:
    root = Path(__file__).resolve().parents[3] / "src" / "omnibase_core"
    sources = [
        root / "handlers/handler_delivery_reference.py",
        *sorted((root / "models/delivery").glob("*.py")),
        *(
            root / "enums" / f"enum_delivery_{name}.py"
            for name in ("path_role", "reference_kind", "resolved_kind", "status")
        ),
    ]
    for source in sources:
        text = source.read_text()
        for literal in ("dev-", "OmniNode", "fixture-producer"):
            assert literal not in "\n".join(text.splitlines()[2:]), source
        literals = [
            node.value
            for node in ast.walk(ast.parse(text))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        for repository in ("omnibase_core", "omnibase_infra", "omniclaude"):
            assert all(repository not in literal for literal in literals), source
    new_files = [
        *sources,
        root / "handlers/handler_delivery_reference_cli.py",
        root / "validation/contracts/delivery_reference.validation.yaml",
        Path(__file__),
        Path(__file__).with_name("test_handler_delivery_reference_cli.py"),
    ]
    for source in new_files:
        assert "protocol_" + "dependencies" not in source.read_text(), source
    tree = ast.parse(sources[0].read_text())
    assert all(
        "protocols" not in (node.module or "")
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert all(
        "protocols" not in alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )


def test_ac9_deterministic_without_protocols_across_json_roundtrip() -> None:
    facts = ModelDeliveryFacts(
        overlay=overlay(),
        paths=(path(),),
        refs=(ref("main", Resolved.BRANCH), ref(path_name=None, location="extra")),
    )

    def rendered(value: ModelDeliveryFacts) -> str:
        return (
            "["
            + ",".join(i.model_dump_json() for i in check_delivery_paths(value))
            + "]"
        )

    assert (
        rendered(facts)
        == rendered(facts)
        == rendered(ModelDeliveryFacts.model_validate_json(facts.model_dump_json()))
    )


def test_paths_missing_refs_and_undeclared_refs_are_fail_closed() -> None:
    issues = check_delivery_paths(
        ModelDeliveryFacts(
            overlay=overlay(),
            paths=(path(),),
            refs=(ref(path_name="missing"), ref(path_name=None)),
        )
    )
    assert [(i.status, i.reason) for i in issues] == [
        (Status.BLOCKED, "no_reference_read"),
        (Status.UNDECLARED, "consumer_not_declared"),
        (Status.UNDECLARED, "consumer_not_declared"),
    ]


@pytest.mark.parametrize("on_path", [False, True])
def test_unlisted_consumer_refused_before_tag_movement(on_path: bool) -> None:
    observed = ref(
        first_resolved_target=SHA,
        resolved_target="b" * 40,
        consumer="marketplace_entry" if on_path else "new_consumer",
    )
    declared = path(consumer="new_consumer" if on_path else "marketplace_entry")
    assert (
        judge_reference(observed, declared, overlay()).reason
        == "unlisted_consumer_kind"
    )


@pytest.mark.parametrize("text", ["a" * 40, "b" * 64])
def test_sha_precedes_greedy_tag_pattern(text: str) -> None:
    assert classify_reference(ref(text), path(), overlay(tag_pattern=".*")) == Kind.SHA


def test_empty_unknown_and_missing_role_permission() -> None:
    assert (
        classify_reference(
            ref("  ", automation_names=("bump/release",)), path(), overlay()
        )
        == Kind.UNKNOWN
    )
    configured = overlay().model_copy(update={"role_permissions": ()})
    assert not judge_reference(ref(), path(), configured).reference_allowed


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tag_pattern", "["),
        ("candidate_tag_pattern", "["),
        ("bump_automation_patterns", ["["]),
        ("consumer_kinds", []),
    ],
)
def test_overlay_rejects_invalid_configuration(field: str, value: object) -> None:
    data = overlay().model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        ModelDeliveryOverlay.model_validate(data)


@pytest.mark.parametrize("pattern", ["[", "no_group"])
def test_discovery_requires_compilable_pattern_with_ref_group(pattern: str) -> None:
    with pytest.raises(ValidationError):
        ModelDeliveryDiscoveryPattern(
            consumer_kind="fixture", file_pattern="*", reference_pattern=pattern
        )


def test_dependency_requires_compilable_pattern_and_ruling() -> None:
    with pytest.raises(ValidationError):
        ModelDeliveryDependencyMechanism(
            mechanism_name="fixture", pattern="[", ruling="declared"
        )
    with pytest.raises(ValidationError):
        ModelDeliveryDependencyMechanism(
            mechanism_name="fixture", pattern=".*", ruling=""
        )


def test_validation_issues_preserve_reason_without_sensitive_context() -> None:
    refused = judge_reference(ref("main", Resolved.BRANCH), path(), overlay())
    allowed = judge_reference(ref(), path(), overlay())
    issues = to_validation_issues((allowed, refused))
    assert len(issues) == 1
    assert issues[0].severity == EnumSeverity.ERROR and issues[0].code == "refused"
    assert issues[0].rule_name == "delivery_reference_refused"
    assert (
        issues[0].context is not None and issues[0].context["reason"] == refused.reason
    )
    assert "[REDACTED]" not in str(issues[0].context)


def test_ac4_undeclared_bump_automation_beside_a_declared_mechanism_is_bump_pr() -> (
    None
):
    """A declared mechanism does not launder a second, undeclared bump workflow."""
    observed = ref(
        "bump/package_floor",
        Resolved.BRANCH,
        automation_names=(".github/workflows/version-bump.yml",),
    )
    issue = judge_reference(observed, path(Role.DEPENDENCY), overlay())
    assert issue.kind == Kind.BUMP_PR and not issue.reference_allowed


def test_ac6_every_read_of_a_path_is_judged_not_only_the_first() -> None:
    issues = check_delivery_paths(
        ModelDeliveryFacts(
            overlay=overlay(),
            paths=(path(),),
            refs=(ref(), ref("main", Resolved.BRANCH)),
        )
    )
    assert [(i.kind, i.reference_allowed) for i in issues] == [
        (Kind.DEV_MERGE_TAG, True),
        (Kind.BRANCH, False),
    ]


def test_ac6_discovered_branch_at_a_declared_location_is_refused() -> None:
    issues = reconcile_consumers(
        ModelDeliveryFacts(
            overlay=overlay(),
            paths=(path(),),
            discovered=(
                ref(path_name=None),
                ref("main", Resolved.BRANCH, path_name=None),
            ),
        )
    )
    assert [(i.kind, i.status) for i in issues] == [(Kind.BRANCH, Status.REFUSED)]
