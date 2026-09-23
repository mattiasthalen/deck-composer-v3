"""Rules and measurements. The first test is the bug gen 1 shipped."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from deck_composer import check as check_module
from deck_composer.check import LAND_FLOOR, checkpoint
from deck_composer.errors import ToolError
from deck_composer.facts import CardFacts
from deck_composer.manabox import parse_deck
from deck_composer.rules import read_rules, read_targets
from tests.helpers import deck_text

ZORALINE = "1 Zoraline, Cosmos Caller (BLB) 242"
ZORALINE_NAME = "Zoraline, Cosmos Caller"
WICK = "Wick, the Whorled Mind"


def table(*texts: str) -> list:
    return [parse_deck(text, path=f"deck{n}.txt") for n, text in enumerate(texts)]


def codes(report, deck: int = 0) -> list[str]:
    return [v.code for v in report.decks[deck].violations]


def one(text: str, facts: CardFacts, rules=None, targets=None):
    return check_module.check(table(text), facts, rules or RULES, targets or TARGETS)


RULES = read_rules(Path("data/categories.json"))
TARGETS = read_targets(Path("data/targets.json"))


# --- the regression -------------------------------------------------------


def test_four_copies_of_a_nonbasic_land_is_a_singleton_violation(card_facts: CardFacts) -> None:
    """Gen 1 shipped `4 Uncharted Haven` against a green singleton check.

    Its duplicate predicate inspected nonland cards only. This is the exact
    false green that ADR-0002 exists to prevent, so it is the first test.
    """
    report = one(deck_text("regression", [ZORALINE], ["4 Uncharted Haven"]), card_facts)
    singleton = [v for v in report.decks[0].violations if v.code == "singleton"]
    assert singleton, "four copies of a nonbasic land must violate singleton"
    assert singleton[0].detail == {"card": "Uncharted Haven", "quantity": 4}
    assert not report.passed


def test_basic_lands_are_exempt_from_singleton(card_facts: CardFacts) -> None:
    report = one(deck_text("basics", [ZORALINE], ["15 Plains", "15 Swamp"]), card_facts)
    assert "singleton" not in codes(report)


def test_a_single_nonbasic_land_is_fine(card_facts: CardFacts) -> None:
    report = one(deck_text("one", [ZORALINE], ["1 Uncharted Haven"]), card_facts)
    assert "singleton" not in codes(report)


def test_a_duplicated_nonland_is_a_singleton_violation(card_facts: CardFacts) -> None:
    report = one(deck_text("spell", [ZORALINE], ["2 Feed the Cycle"]), card_facts)
    assert "singleton" in codes(report)


# --- the other hard rules -------------------------------------------------


def test_a_banned_card_is_not_legal(card_facts: CardFacts) -> None:
    report = one(deck_text("banned", [ZORALINE], ["1 Prophet of Kruphix"]), card_facts)
    found = [v for v in report.decks[0].violations if v.code == "not_legal"]
    assert found and found[0].detail["card"] == "Prophet of Kruphix"


def test_a_card_outside_the_commanders_identity_violates(card_facts: CardFacts) -> None:
    """Zoraline is Orzhov; Bakersbane Duo is green."""
    report = one(deck_text("identity", [ZORALINE], ["1 Bakersbane Duo"]), card_facts)
    found = [v for v in report.decks[0].violations if v.code == "color_identity"]
    assert found and found[0].detail["outside"] == ["G"]


def test_a_card_inside_the_identity_does_not_violate(card_facts: CardFacts) -> None:
    report = one(deck_text("identity", [ZORALINE], ["1 Vengeful Bloodwitch"]), card_facts)
    assert "color_identity" not in codes(report)


def test_a_game_changer_violates_at_bracket_two(card_facts: CardFacts) -> None:
    report = one(deck_text("gc", [ZORALINE], ["1 Vampiric Tutor"]), card_facts)
    assert "game_changer" in codes(report)


def test_a_deck_that_is_not_a_hundred_cards_violates(card_facts: CardFacts) -> None:
    report = one(deck_text("short", [ZORALINE], ["1 Feed the Cycle"]), card_facts)
    found = [v for v in report.decks[0].violations if v.code == "deck_size"]
    assert found and found[0].detail == {"size": 2, "expected": 100}


def test_a_deck_below_the_land_floor_violates(card_facts: CardFacts) -> None:
    report = one(deck_text("lands", [ZORALINE], ["10 Plains"]), card_facts)
    found = [v for v in report.decks[0].violations if v.code == "land_floor"]
    assert found and found[0].detail == {"lands": 10, "floor": LAND_FLOOR}


def test_a_deck_at_the_land_floor_does_not_violate(card_facts: CardFacts) -> None:
    report = one(deck_text("lands", [ZORALINE], ["18 Plains", "17 Swamp"]), card_facts)
    assert "land_floor" not in codes(report)


def test_a_commander_that_is_not_a_legendary_creature_violates(card_facts: CardFacts) -> None:
    report = one(deck_text("bad", ["1 Feed the Cycle"], ["1 Plains"]), card_facts)
    assert "commander_ineligible" in codes(report)


# --- the maybeboard -------------------------------------------------------


def test_the_maybeboard_never_counts(card_facts: CardFacts) -> None:
    """It holds unowned cards, so it counts towards nothing."""
    text = deck_text(
        "maybe",
        [ZORALINE],
        ["18 Plains", "17 Swamp"],
        maybeboard=["1 Sol Ring", "4 Uncharted Haven"],
    )
    report = one(text, card_facts)
    assert report.decks[0].metrics["size"] == 36
    assert report.decks[0].metrics["maybeboard"] == 5
    assert "singleton" not in codes(report)


def test_an_unowned_maybeboard_name_is_not_resolved(card_facts: CardFacts) -> None:
    """Sol Ring is not in the card facts; the maybeboard must not make that a failure."""
    text = deck_text("maybe", [ZORALINE], ["1 Plains"], maybeboard=["1 Sol Ring"])
    report = one(text, card_facts)
    assert report.decks[0].metrics["maybeboard"] == 1


# --- ownership, which is a table property ---------------------------------


def test_ownership_is_summed_across_the_whole_table(card_facts: CardFacts) -> None:
    """Six Moonrise Clerics are owned five; four decks each taking one is fine."""
    decks = [deck_text(f"d{n}", [ZORALINE], ["1 Moonrise Cleric"]) for n in range(4)]
    report = check_module.check(table(*decks), card_facts, RULES, TARGETS)
    assert not [v for v in report.violations if v.code == "ownership"]


def test_the_table_overdrawing_a_card_violates(card_facts: CardFacts) -> None:
    """Vengeful Bloodwitch is owned once; two decks cannot both play it."""
    decks = [deck_text(f"d{n}", [ZORALINE], ["1 Vengeful Bloodwitch"]) for n in range(2)]
    report = check_module.check(table(*decks), card_facts, RULES, TARGETS)
    found = [v for v in report.violations if v.code == "ownership"]
    assert found and found[0].detail == {
        "card": "Vengeful Bloodwitch",
        "used": 2,
        "owned": 1,
    }


def test_basics_are_owned_like_any_other_card(card_facts: CardFacts) -> None:
    """ADR-0005: no exemption. The export holds 14 Plains."""
    decks = [deck_text(f"d{n}", [ZORALINE], ["10 Plains"]) for n in range(2)]
    report = check_module.check(table(*decks), card_facts, RULES, TARGETS)
    found = [v for v in report.violations if v.code == "ownership"]
    assert found and found[0].detail == {"card": "Plains", "used": 20, "owned": 14}


def test_a_token_printing_does_not_inflate_the_cards_ownership(card_facts: CardFacts) -> None:
    """Starscape Cleric is 6 as a card and 2 more as a TBLB token.

    Summing owned quantity by name would say 8. Ownership joins through
    printings, so the card is 6 and the token is counted apart.
    """
    entry = card_facts.card("Starscape Cleric")
    assert entry is not None and entry.owned == 6
    token = next(t for t in card_facts.tokens if t.token.name == "Starscape Cleric")
    assert token.owned == 2


# --- the basic budget, a table-level fact ---------------------------------


def test_the_basic_budget_is_reported_at_the_table(card_facts: CardFacts) -> None:
    decks = [deck_text(f"d{n}", [ZORALINE], ["5 Plains"]) for n in range(2)]
    report = check_module.check(table(*decks), card_facts, RULES, TARGETS)
    budget = report.metrics["basic_budget"]["Plains"]
    assert budget["owned"] == 14
    assert budget["used"] == 10
    assert budget["remaining"] == 4


# --- metrics --------------------------------------------------------------


def test_the_tribal_core_is_two_numbers_never_one(card_facts: CardFacts) -> None:
    """Zoraline is a Bat Cleric, so both subtypes are measured and neither is chosen."""
    text = deck_text("bats", [ZORALINE], ["1 Starscape Cleric", "1 Moonrise Cleric"])
    core = one(text, card_facts).decks[0].metrics["tribal_core"]
    assert set(core) == {"Bat", "Cleric"}
    for numbers in core.values():
        assert set(numbers) == {"type_line", "text_mention", "total", "ceiling"}
        assert numbers["total"] == numbers["type_line"] + numbers["text_mention"]
        # The pool ceiling is the same two numbers, so a deck can be read
        # against what its colours could actually field.
        assert numbers["ceiling"]["total"] >= numbers["total"]


def test_metrics_measure_the_deck(card_facts: CardFacts) -> None:
    text = deck_text("m", [ZORALINE], ["18 Plains", "17 Swamp", "1 Feed the Cycle"])
    metrics = one(text, card_facts).decks[0].metrics
    assert metrics["lands"] == 35
    assert metrics["basics"] == {"Plains": 18, "Swamp": 17}
    assert metrics["nonbasic_lands"] == 0
    assert metrics["color_sources"] == {"W": 18, "B": 17}
    assert metrics["size"] == 37  # commander plus 36


def test_the_spread_is_reported_without_a_verdict(card_facts: CardFacts) -> None:
    """The band that would judge this spread is not yet decided, so none is emitted."""
    decks = [deck_text("a", [ZORALINE], ["20 Plains"]), deck_text("b", [ZORALINE], ["10 Plains"])]
    spread = check_module.check(table(*decks), card_facts, RULES, TARGETS).metrics["spread"]
    assert spread["lands"] == {"values": [20, 10], "min": 10, "max": 20, "spread": 10}
    assert "verdict" not in spread and "band" not in spread


def test_unsettled_fields_are_absent_not_null(card_facts: CardFacts) -> None:
    """A null invites a zero; an absent field cannot be cited by a playbook."""
    report = one(deck_text("m", [ZORALINE], ["1 Plains"]), card_facts).to_dict()
    metrics = report["decks"][0]["metrics"]
    for unsettled in ("removal", "draw", "ramp", "mass_land_denial", "extra_turns"):
        assert unsettled not in metrics
    assert "balance" not in report["table"]


# --- contract failures ----------------------------------------------------


def test_a_name_the_card_facts_lack_is_a_contract_failure(card_facts: CardFacts) -> None:
    with pytest.raises(ToolError) as caught:
        one(deck_text("x", [ZORALINE], ["1 Black Lotus"]), card_facts)
    assert caught.value.error == "unknown_card"
    assert caught.value.detail["card"] == "Black Lotus"


def test_a_face_name_resolves_to_its_card(card_facts: CardFacts) -> None:
    report = one(deck_text("face", [ZORALINE], ["1 Honorbound Page"]), card_facts)
    assert report.decks[0].metrics["size"] == 2


# --- the checkpoint -------------------------------------------------------


def test_the_checkpoint_computes_before_any_deck_exists(card_facts: CardFacts) -> None:
    """ADR-0008: tribal core and basic headroom from the card facts and a commander."""
    view = checkpoint(
        card_facts, ["Zoraline, Cosmos Caller", "Wick, the Whorled Mind"], RULES, TARGETS
    )
    zoraline = view["decks"][0]
    assert zoraline["color_identity"] == ["W", "B"]
    assert zoraline["violations"] == []
    assert set(zoraline["metrics"]["tribal_core"]) == {"Bat", "Cleric"}
    assert zoraline["metrics"]["pool"]["legal_nonland_names"] > 0
    assert view["table"]["metrics"]["basic_budget"]["Plains"]["owned"] == 14


def test_the_checkpoint_reports_the_snapshot(card_facts: CardFacts) -> None:
    view = checkpoint(card_facts, ["Zoraline, Cosmos Caller"], RULES, TARGETS)
    assert view["snapshot"]["export_sha256"].startswith("sha256:")
    assert view["snapshot"]["card_facts_refreshed"] == "2026-09-20"


# --- the commander does not count toward its own tribal core --------------


def test_a_commander_is_excluded_from_its_own_tribal_core(card_facts: CardFacts) -> None:
    """The number answers how tribal the 99 can be, and the commander is not one.

    Zoraline is a Bat. Counting her would add a constant 1 to every candidate,
    which carries no comparative information at the selection checkpoint.
    """
    identity = ("W", "B")
    with_her = check_module.tribal_core(card_facts, "Bat", identity)
    without = check_module.tribal_core(
        card_facts, "Bat", identity, excluding="Zoraline, Cosmos Caller"
    )
    assert without["type_line"] == with_her["type_line"] - 1


def test_the_checkpoint_excludes_each_commander_from_its_own_core(
    card_facts: CardFacts,
) -> None:
    view = checkpoint(card_facts, ["Zoraline, Cosmos Caller"], RULES, TARGETS)
    bats = view["decks"][0]["metrics"]["tribal_core"]["Bat"]["ceiling"]
    plain = check_module.tribal_core(card_facts, "Bat", ("W", "B"))
    assert bats["type_line"] == plain["type_line"] - 1


def test_a_commander_in_the_deck_is_excluded_from_the_deck_core(
    card_facts: CardFacts,
) -> None:
    text = deck_text("bats", [ZORALINE], ["1 Starscape Cleric"])
    core = one(text, card_facts).decks[0].metrics["tribal_core"]["Bat"]
    assert core["type_line"] == 1  # Starscape Cleric only, never Zoraline


# --- bracket 2 violation categories ---------------------------------------


def test_an_extra_turn_card_violates_at_bracket_two(card_facts: CardFacts) -> None:
    """Detected by pattern over oracle data, never by a label the composer applied."""
    from deck_composer.rules import read_rules

    payload = json.loads(Path("data/categories.json").read_text(encoding="utf-8"))
    payload["categories"]["extra_turns"]["include"] = ["Feed the Cycle"]
    path = Path(tempfile.mkdtemp()) / "categories.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    report = one(deck_text("x", [ZORALINE], ["1 Feed the Cycle"]), card_facts, read_rules(path))
    assert "extra_turns" in codes(report)


def test_a_clean_deck_trips_no_category_violation(card_facts: CardFacts) -> None:
    report = one(deck_text("x", [ZORALINE], ["18 Plains", "17 Swamp"]), card_facts)
    assert "extra_turns" not in codes(report)
    assert "mass_land_denial" not in codes(report)


# --- ceilings beside targets ----------------------------------------------


def test_a_metric_reports_its_target_and_its_ceiling(card_facts: CardFacts) -> None:
    """`ramp 2 (target 10, ceiling 2)` tells a build failure from a collection fact."""
    report = one(deck_text("x", [ZORALINE], ["18 Plains", "17 Swamp"]), card_facts)
    ramp = report.decks[0].metrics["categories"]["ramp"]
    assert set(ramp) == {"count", "target", "ceiling"}
    assert ramp["target"] == 10
    assert ramp["ceiling"] >= ramp["count"]


def test_a_target_the_collection_cannot_meet_is_still_reported(
    card_facts: CardFacts,
) -> None:
    """Sweepers stays at 2 against a pool holding fewer. The ceiling says why."""
    report = one(deck_text("x", [ZORALINE], ["1 Plains"]), card_facts)
    sweepers = report.decks[0].metrics["categories"]["sweepers"]
    assert sweepers["target"] == 2
    assert "ceiling" in sweepers


def test_the_ceiling_comes_from_colour_identity_alone(card_facts: CardFacts) -> None:
    """A ceiling that moved with build order could not be reasoned about."""
    alone = one(deck_text("a", [ZORALINE], ["1 Plains"]), card_facts)
    decks = [deck_text(f"d{n}", [ZORALINE], ["1 Vengeful Bloodwitch"]) for n in range(3)]
    crowded = check_module.check(table(*decks), card_facts, RULES, TARGETS)
    assert (
        alone.decks[0].metrics["categories"]["draw"]["ceiling"]
        == crowded.decks[0].metrics["categories"]["draw"]["ceiling"]
    )


# --- balance is a spread with no threshold --------------------------------


def test_the_spread_covers_four_axes_and_judges_none(card_facts: CardFacts) -> None:
    decks = [deck_text("a", [ZORALINE], ["20 Plains"]), deck_text("b", [ZORALINE], ["10 Plains"])]
    spread = check_module.check(table(*decks), card_facts, RULES, TARGETS).metrics["spread"]
    assert set(spread) == {
        "note",
        "lands",
        "average_mana_value",
        "creatures",
        "targeted_interaction",
    }
    for axis in ("lands", "average_mana_value", "creatures", "targeted_interaction"):
        assert set(spread[axis]) == {"values", "min", "max", "spread"}
        assert "verdict" not in spread[axis] and "passed" not in spread[axis]


def test_the_report_names_the_rules_it_ran_under(card_facts: CardFacts) -> None:
    report = one(deck_text("x", [ZORALINE], ["1 Plains"]), card_facts).to_dict()
    assert report["snapshot"]["rules_version"]
    assert report["snapshot"]["rules_hash"].startswith("sha256:")
    assert report["snapshot"]["targets_version"]


# --- the estimate the commanders were picked on --------------------------


def test_the_measured_budget_is_compared_against_the_estimate(
    card_facts: CardFacts,
) -> None:
    """The commanders were chosen partly on the checkpoint's estimate (ADR-0005).

    Two Orzhov decks estimate an even 35-land split, so roughly 35 Plains. Both
    lists here take 5, so the estimate asked for far more than the build used.
    """
    decks = [deck_text(f"d{n}", [ZORALINE], ["5 Plains"]) for n in range(2)]
    metrics = check_module.check(table(*decks), card_facts, RULES, TARGETS).metrics
    plains = metrics["basic_budget"]["Plains"]
    assert plains["used"] == 10
    assert plains["estimated_used"] == 35
    assert plains["divergence"] == -25  # conservative: the safe direction


def test_an_estimate_that_was_too_generous_is_named(card_facts: CardFacts) -> None:
    """The dangerous direction: the build wants more than the checkpoint predicted.

    It admits a commander set the collection cannot support, and nothing finds
    that out until four land bases exist.
    """
    decks = [deck_text(f"d{n}", [ZORALINE], ["30 Plains"]) for n in range(2)]
    metrics = check_module.check(table(*decks), card_facts, RULES, TARGETS).metrics
    assert metrics["basic_budget"]["Plains"]["divergence"] == 25
    assert "Plains" in metrics["estimate"]["generous_for"]
    assert "generous" in metrics["estimate"]["divergence"]


def test_an_unbuilt_seat_is_still_charged_to_the_budget(card_facts: CardFacts) -> None:
    """Otherwise the first deck built looks far cheaper than it is.

    Zoraline's list takes 5 Plains. Wick is unbuilt, and being three-colour his
    seat is estimated to want roughly a third of a 35-land floor in each of his
    colours. The remaining budget must already carry that.
    """
    deck = deck_text("d", [ZORALINE], ["5 Plains"])
    report = check_module.check(table(deck), card_facts, RULES, TARGETS, pending=[WICK])
    swamp = report.metrics["basic_budget"]["Swamp"]
    assert swamp["unbuilt_estimate"] == 12  # a third of 35, rounded
    assert swamp["remaining"] == swamp["owned"] - swamp["used"] - 12
    assert report.metrics["seats_unbuilt"] == 1


def test_the_estimate_a_seat_carries_is_the_one_it_is_later_judged_against(
    card_facts: CardFacts,
) -> None:
    """A comparison to an estimate means nothing unless it is the same estimate.

    What the checkpoint charges an unbuilt seat must equal what a later run
    treats as that seat's baseline, or the divergence silently measures against
    a figure nobody ever saw.
    """
    at_checkpoint = checkpoint(card_facts, [ZORALINE_NAME], RULES, TARGETS)
    charged = at_checkpoint["table"]["metrics"]["basic_budget"]["Plains"]["unbuilt_estimate"]

    once_built = check_module.check(
        table(deck_text("d", [ZORALINE], ["1 Plains"])), card_facts, RULES, TARGETS
    ).metrics
    assert charged == once_built["basic_budget"]["Plains"]["estimated_used"]


def test_a_checkpoint_carries_no_divergence(card_facts: CardFacts) -> None:
    """Nothing is measured yet, so there is nothing to compare; absent, not zero."""
    view = checkpoint(card_facts, [ZORALINE_NAME], RULES, TARGETS)
    plains = view["table"]["metrics"]["basic_budget"]["Plains"]
    assert "unbuilt_estimate" in plains
    assert "divergence" not in plains and "estimated_used" not in plains
    assert "estimate" not in view["table"]["metrics"]


def test_a_projected_overrun_is_named_not_blocked(card_facts: CardFacts) -> None:
    """Part of the projection is an estimate, and this project does not block on one.

    Measured overuse is already an ownership violation. This names the basics a
    part-built table is on course to run out of, which is the whole payoff of
    building the scarcest basic first: seen at deck one, not deck four.
    """
    deck = deck_text("d", [ZORALINE], ["12 Swamp"])
    report = check_module.check(table(deck), card_facts, RULES, TARGETS, pending=[WICK, WICK])
    metrics = report.metrics
    assert metrics["basic_budget"]["Swamp"]["remaining"] < 0
    assert "Swamp" in metrics["overcommitted"]
    assert not [v for v in report.violations if v.code == "ownership"]


def test_a_table_within_budget_names_nothing(card_facts: CardFacts) -> None:
    deck = deck_text("d", [ZORALINE], ["1 Swamp"])
    metrics = check_module.check(table(deck), card_facts, RULES, TARGETS).metrics
    assert metrics["overcommitted"] == []


# --- findings from the review of PR #1 ------------------------------------


def _without(facts: CardFacts, name: str) -> CardFacts:
    """The card facts after trading away every copy of `name` and refreshing.

    ADR-0011 keeps a card the project has seen at `owned` zero, so a basic the
    owner has run out of is still in the card facts; it is not unknown.
    """
    import dataclasses

    return dataclasses.replace(
        facts,
        cards=tuple(
            dataclasses.replace(e, owned=0, owned_by_printing=tuple(0 for _ in e.owned_by_printing))
            if e.card.name == name
            else e
            for e in facts.cards
        ),
    )


def test_a_checkpoint_never_certifies_the_table(card_facts: CardFacts) -> None:
    """`passed` is withheld at a checkpoint; `next` must not say it in prose.

    It said "No violations. Render the decklists" before any deck existed —
    gen 1's false green in a different field.
    """
    report = checkpoint(card_facts, [ZORALINE_NAME], RULES, TARGETS)
    assert "passed" not in report
    assert "no violations" not in report["next"].lower()
    assert "render" not in report["next"].lower()
    assert "checkpoint" in report["next"]


def test_a_checkpoint_counts_violations_at_unbuilt_seats(card_facts: CardFacts) -> None:
    """An ineligible commander is a violation even while its deck is unbuilt."""
    report = checkpoint(card_facts, ["Feed the Cycle"], RULES, TARGETS)
    assert report["decks"][0]["violations"][0]["violation"] == "commander_ineligible"
    assert report["next"].startswith("1 violation")


def test_a_part_built_table_is_not_certified(card_facts: CardFacts) -> None:
    """Clean built seats must still not produce "render the decklists".

    The built seat is made clean on purpose: a seat with violations of its own
    makes `next` report them, which never reaches the false green at all.
    """
    import dataclasses

    deck = deck_text("d", [ZORALINE], ["1 Plains"])
    report = check_module.check(table(deck), card_facts, RULES, TARGETS, pending=[WICK])
    clean = dataclasses.replace(
        report,
        violations=(),
        decks=tuple(dataclasses.replace(d, violations=()) for d in report.decks),
    )
    assert clean.passed is False
    assert "render" not in clean.to_dict()["next"].lower()
    assert "unbuilt" in clean.to_dict()["next"]


def test_an_empty_table_does_not_pass_vacuously(card_facts: CardFacts) -> None:
    assert check_module.check((), card_facts, RULES, TARGETS, pending=[WICK]).passed is False


def test_a_basic_owned_at_zero_keeps_its_row(card_facts: CardFacts) -> None:
    """The row that vanished was the one the basic budget exists to show.

    With no Swamps owned, a black seat's demand was charged nowhere: no Swamp
    row and nothing overcommitted, on the table ADR-0005 makes load-bearing.
    """
    facts = _without(card_facts, "Swamp")
    metrics = checkpoint(facts, [ZORALINE_NAME], RULES, TARGETS)["table"]["metrics"]
    swamp = metrics["basic_budget"]["Swamp"]
    assert swamp["owned"] == 0
    assert swamp["unbuilt_estimate"] > 0
    assert swamp["remaining"] < 0
    assert "Swamp" in metrics["overcommitted"]


def test_a_built_deck_is_charged_for_a_basic_owned_at_zero(card_facts: CardFacts) -> None:
    facts = _without(card_facts, "Swamp")
    report = check_module.check(
        table(deck_text("d", [ZORALINE], ["18 Swamp"])), facts, RULES, TARGETS
    )
    assert report.metrics["basic_budget"]["Swamp"] == {
        "owned": 0,
        "used": 18,
        "remaining": -18,
        "estimated_used": 18,
        "divergence": 0,
    }
    assert "Swamp" in report.metrics["overcommitted"]
    assert any(v.code == "ownership" for v in report.violations)


def test_the_budget_always_carries_the_five_basics(card_facts: CardFacts) -> None:
    for facts in (card_facts, _without(card_facts, "Island")):
        budget = checkpoint(facts, [ZORALINE_NAME], RULES, TARGETS)["table"]["metrics"][
            "basic_budget"
        ]
        assert {"Plains", "Island", "Swamp", "Mountain", "Forest"} <= set(budget)


@pytest.mark.parametrize(
    "lines",
    [
        ["20 Forest (BLB) 280", "15 Forest (BLB) 281"],  # the reviewer's case
        ["20 Forest (FDN) 280", "15 Forest"],  # pinned beside bare
    ],
)
def test_one_basic_on_two_lines_is_summed(card_facts: CardFacts, lines: list[str]) -> None:
    """Keyed by name, the second line overwrote the first: Forest 15 beside lands 35."""
    metrics = one(deck_text("d", [ZORALINE], lines), card_facts).decks[0].metrics
    assert metrics["basics"] == {"Forest": 35}
    assert sum(metrics["basics"].values()) == metrics["lands"]


# --- which seat ADR-0005 builds first -------------------------------------


def _seat(name: str, colours: str) -> dict:
    return {"commander": [name], "color_identity": list(colours)}


REAL_POOL = Path("data/card_facts.json")


def _budget(**remaining: tuple[int, int]) -> dict:
    """basic name -> (owned, remaining)."""
    return {name: {"owned": o, "used": 0, "remaining": r} for name, (o, r) in remaining.items()}


def test_the_seat_with_most_colours_is_built_first_not_the_largest_claim() -> None:
    """The rejected rule built the largest claim, and so never the three-colour seat.

    A two-colour black seat claims about 18 Swamps and a three-colour one about 12,
    but the three-colour estimate is the unreliable one, so it is measured first.
    """
    basics = _budget(Swamp=(38, -9), Plains=(40, 5), Island=(49, 37), Mountain=(42, 13))
    result = check_module.scarcest_basic(basics, [_seat("Two", "WB"), _seat("Three", "UBR")])
    assert result is not None
    assert result["basic"] == "Swamp"
    assert {c["commander"] for c in result["claimants"]} == {"Two", "Three"}
    assert result["build_first"] == "Three"


def test_a_tie_on_colours_is_always_a_tie_on_claim_today() -> None:
    """ADR-0005's middle tie-break, to the largest claim, cannot bind under an even split.

    The claim is a function of colour count alone, so seats that tie on colours
    tie on claim as well, and the decision always falls through to the name. The
    clause stays because a colour-weighted estimate would make it live. This
    pins that it is not live now, so an estimator change that makes it bind
    fails here, and that clause gets a test of its own rather than borrowing
    this one's name.
    """
    two_colour = [("W", "B"), ("B", "G"), ("U", "B"), ("B", "R")]
    assert len({check_module._estimated_demand([i])["Swamp"] for i in two_colour}) == 1
    basics = _budget(Swamp=(38, -20), Plains=(40, 20), Forest=(54, 36))
    result = check_module.scarcest_basic(basics, [_seat("Two", "WB"), _seat("Other two", "BG")])
    assert result is not None
    assert {c["estimated"] for c in result["claimants"]} == {18}
    assert result["build_first"] == "Other two"  # decided by name: the claims are equal


def test_an_exact_tie_breaks_on_commander_name_not_input_order() -> None:
    """Swap two tied seats in the input and the seat built first must not change.

    Input order is the composer's; letting it break the tie would let the order a
    list was written in steer a tool decision (ADR-0002). The break is on the
    commander name that sorts first, which nothing the composer does can move.
    """
    basics = _budget(Swamp=(38, -9), Plains=(40, 5), Forest=(54, 20))
    for seats in (
        [_seat("Zeta", "WB"), _seat("Alpha", "WB")],
        [_seat("Alpha", "WB"), _seat("Zeta", "WB")],
    ):
        result = check_module.scarcest_basic(basics, seats)
        assert result is not None and result["build_first"] == "Alpha"


def test_nothing_in_the_seat_block_depends_on_input_order() -> None:
    """Not only the decision: the whole block, claimants included, is order-free."""
    from itertools import permutations

    basics = _budget(
        Swamp=(38, -9), Plains=(40, 5), Island=(49, 37), Mountain=(42, 13), Forest=(54, 20)
    )
    seats = [_seat("Three", "UBR"), _seat("Orzhov", "WB"), _seat("Golgari", "BG")]
    blocks = [check_module.scarcest_basic(basics, list(order)) for order in permutations(seats)]
    assert all(block == blocks[0] for block in blocks)
    assert blocks[0] is not None
    assert [c["commander"] for c in blocks[0]["claimants"]] == ["Golgari", "Orzhov", "Three"]


def test_the_tie_that_decides_the_second_seat_here_is_broken_by_name() -> None:
    """The three seats left once Wick is built: Camellia and Zoraline tie on Swamp.

    Against the real collection, two colours each, about 18 Swamps each — the
    tie is the common case, so this is the break that picks the second seat.
    """
    from deck_composer.facts import read as read_facts

    facts = read_facts(REAL_POOL)
    three = ["Zoraline, Cosmos Caller", "Camellia, the Seedmiser", "Mabel, Heir to Cragflame"]
    for order in (three, list(reversed(three))):
        scarcest = checkpoint(facts, order, RULES, TARGETS)["table"]["metrics"]["scarcest_basic"]
        assert scarcest["basic"] == "Swamp"
        assert {c["commander"] for c in scarcest["claimants"]} == {
            "Camellia, the Seedmiser",
            "Zoraline, Cosmos Caller",
        }
        assert scarcest["build_first"] == "Camellia, the Seedmiser"


def test_scarcest_means_least_headroom_not_least_owned() -> None:
    """39 of 40 Plains claimed is scarcer than 10 of 38 Swamps (ADR-0005)."""
    basics = _budget(Plains=(40, 1), Swamp=(38, 28))
    result = check_module.scarcest_basic(basics, [_seat("Orzhov", "WB")])
    assert result is not None and result["basic"] == "Plains"


def test_a_basic_no_unbuilt_seat_claims_is_never_the_scarcest() -> None:
    """Built seats may have spent it, but it cannot be measured early by anyone."""
    basics = _budget(Forest=(54, -50), Swamp=(38, -2), Plains=(40, 10))
    result = check_module.scarcest_basic(basics, [_seat("Orzhov", "WB")])
    assert result is not None and result["basic"] == "Swamp"


def test_no_claimed_basic_names_no_seat() -> None:
    """A colourless commander claims no basic; there is nothing to build first."""
    assert check_module.scarcest_basic(_budget(Swamp=(38, 38)), [_seat("Page", "")]) is None


@pytest.mark.parametrize(
    ("commanders", "basic", "claimants"),
    [
        (
            [WICK, "Mabel, Heir to Cragflame", "Camellia, the Seedmiser", ZORALINE_NAME],
            "Swamp",
            {WICK, "Camellia, the Seedmiser", ZORALINE_NAME},
        ),
        (
            [ZORALINE_NAME, "Camellia, the Seedmiser", "Mabel, Heir to Cragflame", WICK],
            "Swamp",
            {WICK, "Camellia, the Seedmiser", ZORALINE_NAME},
        ),
        (
            # Swamp is not tight here at all; Wick's unreliable claim is on Mountain.
            [WICK, "Mabel, Heir to Cragflame", "Finneas, Ace Archer", "Alania, Divergent Storm"],
            "Mountain",
            {WICK, "Mabel, Heir to Cragflame", "Alania, Divergent Storm"},
        ),
    ],
)
def test_wick_is_built_first_at_this_table_for_the_stated_reason(
    commanders: list[str], basic: str, claimants: set[str]
) -> None:
    """Against the real collection. Wick comes first because his estimate is the
    least reliable claim on the tightest basic, not because he is black — the
    third table shows the difference, since there it is Mountain that binds.
    """
    from deck_composer.facts import read as read_facts

    view = checkpoint(read_facts(REAL_POOL), commanders, RULES, TARGETS)
    scarcest = view["table"]["metrics"]["scarcest_basic"]
    assert scarcest["basic"] == basic
    assert {c["commander"] for c in scarcest["claimants"]} == claimants
    assert scarcest["build_first"] == WICK
    assert WICK in view["next"]


def test_a_part_built_table_names_the_next_seat(card_facts: CardFacts) -> None:
    """With the built seat clean: violations come first in `next`, rightly, so a
    seat carrying its own would never reach the sentence that names the next one.
    """
    import dataclasses

    deck = deck_text("d", [ZORALINE], ["1 Plains"])
    report = check_module.check(table(deck), card_facts, RULES, TARGETS, pending=[WICK])
    clean = dataclasses.replace(
        report,
        violations=(),
        decks=tuple(dataclasses.replace(d, violations=()) for d in report.decks),
    )
    assert clean.metrics["scarcest_basic"]["build_first"] == WICK
    assert WICK in clean.to_dict()["next"]


def test_violations_come_before_the_next_seat(card_facts: CardFacts) -> None:
    """Fixing what is built outranks building more; the seat stays in the metrics."""
    deck = deck_text("d", [ZORALINE], ["1 Plains"])
    report = check_module.check(table(deck), card_facts, RULES, TARGETS, pending=[WICK])
    assert report.violation_count
    assert report.to_dict()["next"].startswith(f"{report.violation_count} violation")
    assert report.metrics["scarcest_basic"]["build_first"] == WICK


def test_a_finished_table_names_no_seat(card_facts: CardFacts) -> None:
    metrics = one(deck_text("d", [ZORALINE], ["1 Plains"]), card_facts).metrics
    assert "scarcest_basic" not in metrics
