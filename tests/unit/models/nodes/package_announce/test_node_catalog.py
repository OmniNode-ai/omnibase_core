# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The catalog is a pure value built from announcements (OMN-21589, A1 AC2, AC5, AC6)."""

from pathlib import Path

import pytest

from omnibase_core.enums.enum_announce_refusal_reason import EnumAnnounceRefusalReason
from omnibase_core.enums.enum_announcement_operation import EnumAnnouncementOperation
from omnibase_core.enums.enum_catalog_entry_state import EnumCatalogEntryState
from omnibase_core.models.nodes.package_announce.model_node_catalog import (
    ModelNodeCatalog,
)
from tests.unit.models.nodes.package_announce.fixture_planted import (
    ANNOUNCER,
    INTRUDER,
    announcement,
    contract_bytes,
    policy,
)

State = EnumCatalogEntryState
WITHDRAW = EnumAnnouncementOperation.WITHDRAW


def _three() -> tuple[ModelNodeCatalog, dict[str, bytes]]:
    """A catalog holding three admitted names from two packages."""
    catalog = ModelNodeCatalog(policy=policy())
    contracts = {
        "fixture_one": (contract_bytes("fixture_one", newline="\r\n"), "alpha-pkg"),
        "fixture_two": (contract_bytes("fixture_two"), "alpha-pkg"),
        "fixture_three": (
            contract_bytes("fixture_three", handler_module="beta_pkg.nodes.t.handler"),
            "beta-pkg",
        ),
    }
    for name, (raw, distribution) in contracts.items():
        catalog, outcome, _ = catalog.apply(
            announcement(raw, name=name, distribution=distribution),
            installed_bytes=raw,
            installed_path=Path(f"/installed/{name}/contract.yaml"),
        )
        assert outcome.accepted
    return catalog, {name: raw for name, (raw, _) in contracts.items()}


@pytest.mark.unit
def test_the_catalog_holds_the_three_names_at_their_hashes() -> None:
    catalog, raws = _three()
    assert set(catalog.entries) == set(raws)
    for name, raw in raws.items():
        entry = catalog.entries[name]
        assert entry.state is State.ADMITTED
        assert entry.content_hash == announcement(raw).content_hash
        assert entry.contract_path == Path(f"/installed/{name}/contract.yaml")


@pytest.mark.unit
def test_apply_never_mutates_the_catalog_it_was_called_on() -> None:
    catalog, _ = _three()
    before = catalog.model_dump(mode="json")
    changed = contract_bytes("fixture_two", extra_topic="onex.evt.fixture.extra.v1")
    next_catalog, _, _ = catalog.apply(
        announcement(changed, name="fixture_two", generation=2),
        installed_bytes=changed,
    )
    assert catalog.model_dump(mode="json") == before
    assert next_catalog is not catalog


@pytest.mark.unit
def test_reannouncing_one_with_changed_bytes_replaces_its_hash_only() -> None:
    catalog, _ = _three()
    changed = contract_bytes("fixture_two", extra_topic="onex.evt.fixture.extra.v1")
    after, outcome, changes = catalog.apply(
        announcement(changed, name="fixture_two", generation=2),
        installed_bytes=changed,
    )
    assert outcome.accepted
    assert (
        after.entries["fixture_two"].content_hash
        != catalog.entries["fixture_two"].content_hash
    ), "falsifier: a stale hash"
    assert after.entries["fixture_two"].generation == 2
    for untouched in ("fixture_one", "fixture_three"):
        assert after.entries[untouched] == catalog.entries[untouched], (
            "falsifier: a changed neighbour"
        )
    assert [c.entry.state for c in changes] == [State.ANNOUNCED, State.ADMITTED]
    assert changes[0].previous_state is State.ADMITTED


@pytest.mark.unit
def test_the_same_bytes_at_a_newer_generation_refresh_the_generation_only() -> None:
    catalog, raws = _three()
    raw = raws["fixture_two"]
    after, outcome, changes = catalog.apply(
        announcement(raw, name="fixture_two", generation=5), installed_bytes=raw
    )
    assert outcome.accepted and changes == ()
    assert after.entries["fixture_two"].generation == 5
    assert after.entries["fixture_two"].state is State.ADMITTED


@pytest.mark.unit
@pytest.mark.parametrize("operation", list(EnumAnnouncementOperation))
@pytest.mark.parametrize("generation", [1, 0 + 1])
def test_older_or_equal_generation_is_rejected_and_counted(
    operation: EnumAnnouncementOperation, generation: int
) -> None:
    catalog, raws = _three()
    held = catalog.entries["fixture_one"].generation
    assert held == 1
    stale = announcement(
        raws["fixture_one"],
        name="fixture_one",
        operation=operation,
        generation=generation,
    )
    after, outcome, changes = catalog.apply(stale, installed_bytes=raws["fixture_one"])
    assert not outcome.accepted
    assert outcome.refusal_reason is EnumAnnounceRefusalReason.STALE_GENERATION
    assert after.stale_generation_rejections == catalog.stale_generation_rejections + 1
    assert after.entries == catalog.entries, "falsifier: a catalog change after either"
    assert changes == ()


@pytest.mark.unit
def test_withdrawal_from_a_non_authoritative_announcer_is_refused() -> None:
    catalog, raws = _three()
    intruder = announcement(
        raws["fixture_one"],
        name="fixture_one",
        operation=WITHDRAW,
        generation=9,
        announcer_id=INTRUDER,
    )
    after, outcome, _ = catalog.apply(intruder)
    assert (
        outcome.refusal_reason is EnumAnnounceRefusalReason.NON_AUTHORITATIVE_ANNOUNCER
    )
    assert after.entries == catalog.entries, "falsifier: a catalog change after either"


@pytest.mark.unit
def test_a_withdrawal_with_no_authoritative_announcer_named_is_refused() -> None:
    catalog = ModelNodeCatalog(policy=policy(authoritative={}))
    raw = contract_bytes("fixture_one")
    after, outcome, _ = catalog.apply(
        announcement(raw, name="fixture_one", operation=WITHDRAW)
    )
    assert not outcome.accepted and after.entries == {}


@pytest.mark.unit
def test_the_authoritative_announcer_withdraws_every_contract_of_a_package() -> None:
    catalog, raws = _three()
    for name in ("fixture_one", "fixture_two"):
        catalog, outcome, _ = catalog.apply(
            announcement(raws[name], name=name, operation=WITHDRAW, generation=2)
        )
        assert outcome.accepted and outcome.state is State.WITHDRAWN
    assert {n for n, e in catalog.entries.items() if e.state is State.ADMITTED} == {
        "fixture_three"
    }, "falsifier: a contract of the removed package still admitted"
    assert catalog.entries["fixture_one"].contract_path == Path(
        "/installed/fixture_one/contract.yaml"
    )


@pytest.mark.unit
def test_a_withdrawal_is_accepted_for_a_name_never_held_and_blocks_resurrection() -> (
    None
):
    catalog = ModelNodeCatalog(policy=policy())
    raw = contract_bytes("never_held")
    catalog, withdrawn, _ = catalog.apply(
        announcement(raw, name="never_held", operation=WITHDRAW, generation=7)
    )
    catalog, late, _ = catalog.apply(
        announcement(raw, name="never_held", generation=3), installed_bytes=raw
    )
    assert withdrawn.accepted and withdrawn.state is State.WITHDRAWN
    assert not late.accepted, (
        "a delayed older announcement must not resurrect the entry"
    )
    assert catalog.entries["never_held"].state is State.WITHDRAWN


@pytest.mark.unit
def test_a_withdrawn_name_can_be_announced_again_at_a_newer_generation() -> None:
    catalog, raws = _three()
    raw = raws["fixture_two"]
    catalog, _, _ = catalog.apply(
        announcement(raw, name="fixture_two", operation=WITHDRAW, generation=2)
    )
    catalog, outcome, _ = catalog.apply(
        announcement(raw, name="fixture_two", generation=3), installed_bytes=raw
    )
    assert outcome.accepted
    assert catalog.entries["fixture_two"].state is State.ADMITTED


@pytest.mark.unit
def test_refusal_by_admission_keeps_a_refused_entry_with_the_typed_reason() -> None:
    catalog = ModelNodeCatalog(policy=policy())
    raw = contract_bytes("planted", handler_module="rogue_pkg.x")
    catalog, outcome, changes = catalog.apply(
        announcement(raw, name="planted"), installed_bytes=raw
    )
    entry = catalog.entries["planted"]
    assert not outcome.accepted and outcome.state is State.REFUSED
    assert entry.state is State.REFUSED
    assert (
        entry.refusal_reason
        is EnumAnnounceRefusalReason.HANDLER_OUTSIDE_TRUSTED_PREFIXES
    )
    assert [c.entry.state for c in changes] == [State.ANNOUNCED, State.REFUSED]


@pytest.mark.unit
def test_a_refused_name_recovers_when_a_fixed_identity_is_announced() -> None:
    catalog = ModelNodeCatalog(policy=policy())
    bad = contract_bytes("planted", handler_module="rogue_pkg.x")
    good = contract_bytes("planted")
    catalog, _, _ = catalog.apply(
        announcement(bad, name="planted"), installed_bytes=bad
    )
    catalog, outcome, _ = catalog.apply(
        announcement(good, name="planted", generation=2), installed_bytes=good
    )
    assert outcome.accepted and catalog.entries["planted"].state is State.ADMITTED


@pytest.mark.unit
def test_the_authoritative_announcer_default_is_the_policys_not_the_codes() -> None:
    assert ANNOUNCER in policy().authoritative_announcers.values()
    assert policy(authoritative={}).authoritative_announcers == {}
